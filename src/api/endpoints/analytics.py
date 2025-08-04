"""
Analytics API endpoints for the Thai search proxy service.

Provides endpoints for accessing search analytics, query patterns, 
performance trends, and search quality metrics.
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from src.utils.logging import get_structured_logger
from src.search_proxy.analytics import analytics_collector


logger = get_structured_logger(__name__)

# Create router
router = APIRouter()


@router.get(
    "/analytics/queries",
    summary="Get query analytics",
    description="""
    Get comprehensive analytics about search queries including:
    - Top queries by frequency
    - Query language distribution
    - Query length patterns
    - Trending queries
    - Zero result and failed query statistics
    """
)
async def get_query_analytics():
    """
    Get query pattern analytics and insights.
    
    Returns:
        Dictionary containing query analytics data
    """
    try:
        analytics = analytics_collector.get_query_analytics()
        
        logger.info(
            "Query analytics retrieved",
            extra={
                "total_unique_queries": analytics["total_unique_queries"],
                "total_query_volume": analytics["total_query_volume"]
            }
        )
        
        return analytics
        
    except Exception as e:
        logger.error("Failed to retrieve query analytics", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve query analytics: {str(e)}"
        )


@router.get(
    "/analytics/sessions",
    summary="Get session analytics",
    description="""
    Get analytics about user search sessions including:
    - Active session count
    - Average session duration
    - Queries per session
    - Session success rates
    - Bounce rates
    """
)
async def get_session_analytics():
    """
    Get session-based analytics and user behavior insights.
    
    Returns:
        Dictionary containing session analytics data
    """
    try:
        analytics = analytics_collector.get_session_analytics()
        
        logger.info(
            "Session analytics retrieved",
            extra={
                "active_sessions": analytics["active_sessions"],
                "completed_sessions": analytics["completed_sessions_today"]
            }
        )
        
        return analytics
        
    except Exception as e:
        logger.error("Failed to retrieve session analytics", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve session analytics: {str(e)}"
        )


@router.get(
    "/analytics/performance-trends",
    summary="Get performance trends",
    description="""
    Get historical performance trends including:
    - Response time trends (average, p95, p99)
    - Request volume over time
    - Success rates
    - Cache hit rates
    - Active session counts
    """
)
async def get_performance_trends(
    hours: int = Query(default=24, ge=1, le=168, description="Number of hours to look back")
):
    """
    Get performance trends over time.
    
    Args:
        hours: Number of hours of historical data to retrieve (1-168)
        
    Returns:
        List of performance trend data points
    """
    try:
        trends = analytics_collector.get_performance_trends(hours=hours)
        
        logger.info(
            "Performance trends retrieved",
            extra={
                "hours": hours,
                "data_points": len(trends)
            }
        )
        
        return {
            "period_hours": hours,
            "data_points": len(trends),
            "trends": trends
        }
        
    except Exception as e:
        logger.error("Failed to retrieve performance trends", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve performance trends: {str(e)}"
        )


@router.get(
    "/analytics/quality-report",
    summary="Get search quality report",
    description="""
    Get comprehensive search quality metrics including:
    - Zero result query analysis
    - Slow query patterns
    - Failed query analysis
    - Quality recommendations
    """
)
async def get_search_quality_report():
    """
    Get search quality metrics and improvement recommendations.
    
    Returns:
        Dictionary containing search quality analysis
    """
    try:
        report = analytics_collector.get_search_quality_report()
        
        logger.info(
            "Search quality report generated",
            extra={
                "zero_results": report["zero_result_queries"]["total_count"],
                "slow_queries": report["slow_queries"]["total_count"],
                "failed_queries": report["failed_queries"]["total_count"],
                "recommendations": len(report["recommendations"])
            }
        )
        
        return report
        
    except Exception as e:
        logger.error("Failed to generate search quality report", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate search quality report: {str(e)}"
        )


@router.get(
    "/analytics/popular-searches",
    summary="Get popular searches",
    description="""
    Get list of most popular search queries with their metrics.
    Useful for understanding user search patterns and optimizing content.
    """
)
async def get_popular_searches(
    limit: int = Query(default=50, ge=1, le=200, description="Number of top queries to return"),
    language: Optional[str] = Query(default=None, description="Filter by language (thai/english/mixed)")
):
    """
    Get popular search queries.
    
    Args:
        limit: Maximum number of queries to return
        language: Optional language filter
        
    Returns:
        List of popular queries with metrics
    """
    try:
        analytics = analytics_collector.get_query_analytics()
        top_queries = analytics["top_queries"]
        
        # Apply language filter if specified
        if language:
            top_queries = [
                q for q in top_queries 
                if q["language"].lower() == language.lower()
            ]
        
        # Apply limit
        top_queries = top_queries[:limit]
        
        logger.info(
            "Popular searches retrieved",
            extra={
                "limit": limit,
                "language_filter": language,
                "results_count": len(top_queries)
            }
        )
        
        return {
            "count": len(top_queries),
            "language_filter": language,
            "queries": top_queries
        }
        
    except Exception as e:
        logger.error("Failed to retrieve popular searches", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve popular searches: {str(e)}"
        )


@router.get(
    "/analytics/trending",
    summary="Get trending searches",
    description="""
    Get currently trending search queries based on recent activity.
    Identifies queries with increasing search frequency.
    """
)
async def get_trending_searches():
    """
    Get trending search queries.
    
    Returns:
        List of trending queries with trend scores
    """
    try:
        analytics = analytics_collector.get_query_analytics()
        trending = analytics.get("trending_queries", [])
        
        logger.info(
            "Trending searches retrieved",
            extra={"trending_count": len(trending)}
        )
        
        return {
            "count": len(trending),
            "timestamp": datetime.now().isoformat(),
            "queries": trending
        }
        
    except Exception as e:
        logger.error("Failed to retrieve trending searches", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve trending searches: {str(e)}"
        )


@router.post(
    "/analytics/export",
    summary="Export analytics data",
    description="""
    Export analytics data to JSON files for offline analysis.
    Creates timestamped export files with query patterns and analytics summaries.
    """
)
async def export_analytics():
    """
    Export analytics data to files.
    
    Returns:
        Export status and file information
    """
    try:
        export_dir = analytics_collector.export_analytics()
        
        logger.info(
            "Analytics data exported",
            extra={"export_dir": str(export_dir)}
        )
        
        return {
            "status": "success",
            "export_directory": str(export_dir),
            "timestamp": datetime.now().isoformat(),
            "message": "Analytics data exported successfully"
        }
        
    except Exception as e:
        logger.error("Failed to export analytics", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export analytics: {str(e)}"
        )


@router.get(
    "/analytics/summary",
    summary="Get analytics summary",
    description="""
    Get a comprehensive summary of all analytics data including:
    - Query analytics
    - Session analytics
    - Performance overview
    - Quality metrics
    """
)
async def get_analytics_summary():
    """
    Get comprehensive analytics summary.
    
    Returns:
        Dictionary containing all analytics summaries
    """
    try:
        summary = {
            "timestamp": datetime.now().isoformat(),
            "query_analytics": analytics_collector.get_query_analytics(),
            "session_analytics": analytics_collector.get_session_analytics(),
            "performance_trends": analytics_collector.get_performance_trends(hours=1),
            "quality_report": analytics_collector.get_search_quality_report()
        }
        
        logger.info("Analytics summary generated")
        
        return summary
        
    except Exception as e:
        logger.error("Failed to generate analytics summary", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate analytics summary: {str(e)}"
        )