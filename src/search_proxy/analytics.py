"""
Search analytics and monitoring for the Thai search proxy service.

This module provides analytics collection, query pattern analysis, and
search performance monitoring capabilities.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import threading
from pathlib import Path

from ..utils.logging import get_structured_logger


logger = get_structured_logger(__name__)


@dataclass
class QueryPattern:
    """Represents a search query pattern."""
    query: str
    normalized_query: str
    frequency: int
    first_seen: datetime
    last_seen: datetime
    avg_response_time_ms: float
    success_rate: float
    language: str
    query_length: int
    contains_thai: bool
    contains_english: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "query": self.query,
            "normalized_query": self.normalized_query,
            "frequency": self.frequency,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "avg_response_time_ms": self.avg_response_time_ms,
            "success_rate": self.success_rate,
            "language": self.language,
            "query_length": self.query_length,
            "contains_thai": self.contains_thai,
            "contains_english": self.contains_english
        }


@dataclass
class SearchSession:
    """Represents a user search session."""
    session_id: str
    start_time: datetime
    last_activity: datetime
    queries: List[str] = field(default_factory=list)
    total_searches: int = 0
    successful_searches: int = 0
    total_results_viewed: int = 0
    avg_response_time_ms: float = 0.0
    
    def add_search(self, query: str, success: bool, response_time_ms: float) -> None:
        """Add a search to the session."""
        self.queries.append(query)
        self.total_searches += 1
        if success:
            self.successful_searches += 1
        self.last_activity = datetime.now()
        # Update average response time
        self.avg_response_time_ms = (
            (self.avg_response_time_ms * (self.total_searches - 1) + response_time_ms) / 
            self.total_searches
        )


@dataclass
class PerformanceTrend:
    """Represents performance trends over time."""
    timestamp: datetime
    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    requests_per_minute: float
    success_rate: float
    cache_hit_rate: float
    active_sessions: int


class SearchAnalyticsCollector:
    """
    Collects and analyzes search patterns and user behavior.
    
    Provides insights into query patterns, user sessions, performance trends,
    and search quality metrics.
    """
    
    def __init__(
        self, 
        analytics_dir: Optional[Path] = None,
        session_timeout_minutes: int = 30,
        pattern_analysis_window_hours: int = 24
    ):
        """
        Initialize the analytics collector.
        
        Args:
            analytics_dir: Directory to store analytics data
            session_timeout_minutes: Minutes before session expires
            pattern_analysis_window_hours: Hours to analyze for patterns
        """
        self.analytics_dir = analytics_dir or Path("/var/log/search-proxy/analytics")
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.pattern_window = timedelta(hours=pattern_analysis_window_hours)
        
        self._lock = threading.Lock()
        
        # Query patterns tracking
        self._query_patterns: Dict[str, QueryPattern] = {}
        self._query_counter = Counter()
        
        # Session tracking
        self._active_sessions: Dict[str, SearchSession] = {}
        self._completed_sessions: List[SearchSession] = []
        
        # Performance trends
        self._performance_trends: List[PerformanceTrend] = []
        
        # Search quality metrics
        self._zero_result_queries: List[Dict[str, Any]] = []
        self._slow_queries: List[Dict[str, Any]] = []
        self._failed_queries: List[Dict[str, Any]] = []
        
        # Popular searches cache
        self._popular_searches_cache: Optional[List[Dict[str, Any]]] = None
        self._cache_timestamp: Optional[datetime] = None
        
        # Ensure analytics directory exists
        self.analytics_dir.mkdir(parents=True, exist_ok=True)
        
        # Start background tasks
        self._start_background_tasks()
    
    def record_search(
        self,
        query: str,
        session_id: Optional[str],
        success: bool,
        response_time_ms: float,
        results_count: int,
        language: str,
        error_type: Optional[str] = None
    ) -> None:
        """
        Record a search event for analytics.
        
        Args:
            query: Search query text
            session_id: Optional session identifier
            success: Whether search succeeded
            response_time_ms: Response time in milliseconds
            results_count: Number of results returned
            language: Detected language
            error_type: Type of error if search failed
        """
        with self._lock:
            # Normalize query for pattern analysis
            normalized_query = self._normalize_query(query)
            
            # Update query patterns
            self._update_query_pattern(
                query, normalized_query, success, 
                response_time_ms, language
            )
            
            # Update session if provided
            if session_id:
                self._update_session(
                    session_id, query, success, response_time_ms
                )
            
            # Track search quality issues
            if results_count == 0 and success:
                self._zero_result_queries.append({
                    "query": query,
                    "timestamp": datetime.now(),
                    "language": language,
                    "session_id": session_id
                })
            
            if response_time_ms > 1000:  # Slow query threshold
                self._slow_queries.append({
                    "query": query,
                    "timestamp": datetime.now(),
                    "response_time_ms": response_time_ms,
                    "language": language
                })
            
            if not success:
                self._failed_queries.append({
                    "query": query,
                    "timestamp": datetime.now(),
                    "error_type": error_type,
                    "language": language
                })
    
    def get_query_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive query analytics.
        
        Returns:
            Dictionary containing query patterns and insights
        """
        with self._lock:
            # Get top query patterns
            top_patterns = sorted(
                self._query_patterns.values(),
                key=lambda p: p.frequency,
                reverse=True
            )[:100]
            
            # Language distribution
            language_dist = Counter()
            for pattern in self._query_patterns.values():
                language_dist[pattern.language] += pattern.frequency
            
            # Query length distribution
            length_buckets = defaultdict(int)
            for pattern in self._query_patterns.values():
                bucket = (pattern.query_length // 10) * 10
                length_buckets[f"{bucket}-{bucket+9}"] += pattern.frequency
            
            # Recent trends
            recent_queries = [
                p for p in self._query_patterns.values()
                if p.last_seen > datetime.now() - timedelta(hours=1)
            ]
            
            return {
                "total_unique_queries": len(self._query_patterns),
                "total_query_volume": sum(p.frequency for p in self._query_patterns.values()),
                "top_queries": [
                    {
                        "query": p.query,
                        "frequency": p.frequency,
                        "avg_response_time_ms": p.avg_response_time_ms,
                        "success_rate": p.success_rate,
                        "language": p.language
                    }
                    for p in top_patterns[:20]
                ],
                "language_distribution": dict(language_dist),
                "query_length_distribution": dict(length_buckets),
                "trending_queries": self._get_trending_queries(),
                "zero_result_queries": len(self._zero_result_queries),
                "slow_queries": len(self._slow_queries),
                "failed_queries": len(self._failed_queries),
                "recent_activity": {
                    "queries_last_hour": len(recent_queries),
                    "avg_response_time_ms": (
                        sum(p.avg_response_time_ms for p in recent_queries) / len(recent_queries)
                        if recent_queries else 0
                    )
                }
            }
    
    def get_session_analytics(self) -> Dict[str, Any]:
        """
        Get session-based analytics.
        
        Returns:
            Dictionary containing session insights
        """
        with self._lock:
            active_count = len(self._active_sessions)
            
            # Session statistics
            if self._completed_sessions:
                avg_session_duration = sum(
                    (s.last_activity - s.start_time).total_seconds()
                    for s in self._completed_sessions
                ) / len(self._completed_sessions)
                
                avg_queries_per_session = sum(
                    s.total_searches for s in self._completed_sessions
                ) / len(self._completed_sessions)
            else:
                avg_session_duration = 0
                avg_queries_per_session = 0
            
            return {
                "active_sessions": active_count,
                "completed_sessions_today": len(self._completed_sessions),
                "avg_session_duration_seconds": avg_session_duration,
                "avg_queries_per_session": avg_queries_per_session,
                "session_success_rate": self._calculate_session_success_rate(),
                "bounce_rate": self._calculate_bounce_rate()
            }
    
    def get_performance_trends(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get performance trends over time.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of performance trend data points
        """
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            trends = [
                {
                    "timestamp": trend.timestamp.isoformat(),
                    "avg_response_time_ms": trend.avg_response_time_ms,
                    "p95_response_time_ms": trend.p95_response_time_ms,
                    "p99_response_time_ms": trend.p99_response_time_ms,
                    "requests_per_minute": trend.requests_per_minute,
                    "success_rate": trend.success_rate,
                    "cache_hit_rate": trend.cache_hit_rate,
                    "active_sessions": trend.active_sessions
                }
                for trend in self._performance_trends
                if trend.timestamp > cutoff_time
            ]
            
            return trends
    
    def get_search_quality_report(self) -> Dict[str, Any]:
        """
        Get search quality metrics and insights.
        
        Returns:
            Dictionary containing search quality metrics
        """
        with self._lock:
            # Analyze zero result queries
            zero_result_patterns = Counter(
                q["query"].lower() for q in self._zero_result_queries
            )
            
            # Analyze slow queries
            slow_query_patterns = Counter(
                q["query"].lower() for q in self._slow_queries
            )
            
            # Error analysis
            error_types = Counter(
                q["error_type"] for q in self._failed_queries
            )
            
            return {
                "zero_result_queries": {
                    "total_count": len(self._zero_result_queries),
                    "top_queries": zero_result_patterns.most_common(10),
                    "percentage_of_total": (
                        len(self._zero_result_queries) / 
                        sum(p.frequency for p in self._query_patterns.values()) * 100
                        if self._query_patterns else 0
                    )
                },
                "slow_queries": {
                    "total_count": len(self._slow_queries),
                    "top_queries": slow_query_patterns.most_common(10),
                    "avg_response_time_ms": (
                        sum(q["response_time_ms"] for q in self._slow_queries) / 
                        len(self._slow_queries)
                        if self._slow_queries else 0
                    )
                },
                "failed_queries": {
                    "total_count": len(self._failed_queries),
                    "error_distribution": dict(error_types),
                    "failure_rate": (
                        len(self._failed_queries) / 
                        sum(p.frequency for p in self._query_patterns.values()) * 100
                        if self._query_patterns else 0
                    )
                },
                "recommendations": self._generate_quality_recommendations()
            }
    
    def export_analytics(self, output_dir: Optional[Path] = None) -> Path:
        """
        Export analytics data to JSON files.
        
        Args:
            output_dir: Directory to export to (defaults to analytics_dir)
            
        Returns:
            Path to the exported data directory
        """
        output_dir = output_dir or self.analytics_dir
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        with self._lock:
            # Export query patterns
            patterns_file = output_dir / f"query_patterns_{timestamp}.json"
            with open(patterns_file, 'w') as f:
                json.dump(
                    [p.to_dict() for p in self._query_patterns.values()],
                    f,
                    indent=2
                )
            
            # Export analytics summary
            summary_file = output_dir / f"analytics_summary_{timestamp}.json"
            with open(summary_file, 'w') as f:
                json.dump({
                    "query_analytics": self.get_query_analytics(),
                    "session_analytics": self.get_session_analytics(),
                    "quality_report": self.get_search_quality_report(),
                    "export_timestamp": datetime.now().isoformat()
                }, f, indent=2)
            
            logger.info(
                "Analytics exported",
                extra={
                    "patterns_file": str(patterns_file),
                    "summary_file": str(summary_file)
                }
            )
            
            return output_dir
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for pattern matching."""
        # Convert to lowercase and strip whitespace
        normalized = query.lower().strip()
        
        # Remove multiple spaces
        normalized = ' '.join(normalized.split())
        
        # TODO: Add more normalization (remove punctuation, etc.)
        
        return normalized
    
    def _update_query_pattern(
        self,
        query: str,
        normalized_query: str,
        success: bool,
        response_time_ms: float,
        language: str
    ) -> None:
        """Update query pattern statistics."""
        if normalized_query not in self._query_patterns:
            self._query_patterns[normalized_query] = QueryPattern(
                query=query,
                normalized_query=normalized_query,
                frequency=0,
                first_seen=datetime.now(),
                last_seen=datetime.now(),
                avg_response_time_ms=response_time_ms,
                success_rate=1.0 if success else 0.0,
                language=language,
                query_length=len(query),
                contains_thai=self._contains_thai(query),
                contains_english=self._contains_english(query)
            )
        else:
            pattern = self._query_patterns[normalized_query]
            pattern.frequency += 1
            pattern.last_seen = datetime.now()
            
            # Update average response time
            pattern.avg_response_time_ms = (
                (pattern.avg_response_time_ms * (pattern.frequency - 1) + response_time_ms) /
                pattern.frequency
            )
            
            # Update success rate
            if success:
                pattern.success_rate = (
                    (pattern.success_rate * (pattern.frequency - 1) + 1) /
                    pattern.frequency
                )
            else:
                pattern.success_rate = (
                    (pattern.success_rate * (pattern.frequency - 1)) /
                    pattern.frequency
                )
    
    def _update_session(
        self,
        session_id: str,
        query: str,
        success: bool,
        response_time_ms: float
    ) -> None:
        """Update session information."""
        if session_id not in self._active_sessions:
            self._active_sessions[session_id] = SearchSession(
                session_id=session_id,
                start_time=datetime.now(),
                last_activity=datetime.now()
            )
        
        session = self._active_sessions[session_id]
        session.add_search(query, success, response_time_ms)
        
        # Check for expired sessions
        self._cleanup_expired_sessions()
    
    def _cleanup_expired_sessions(self) -> None:
        """Move expired sessions to completed list."""
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, session in self._active_sessions.items():
            if current_time - session.last_activity > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            session = self._active_sessions.pop(session_id)
            self._completed_sessions.append(session)
    
    def _get_trending_queries(self) -> List[Dict[str, Any]]:
        """Identify trending queries based on recent activity."""
        # Simple trending: queries with increasing frequency
        trending = []
        
        for pattern in self._query_patterns.values():
            if pattern.frequency > 5:  # Minimum threshold
                # Check if query is recent and frequent
                if pattern.last_seen > datetime.now() - timedelta(hours=1):
                    trending.append({
                        "query": pattern.query,
                        "frequency": pattern.frequency,
                        "trend_score": pattern.frequency / max(1, (datetime.now() - pattern.first_seen).total_seconds() / 3600)
                    })
        
        # Sort by trend score
        trending.sort(key=lambda x: x["trend_score"], reverse=True)
        
        return trending[:10]
    
    def _calculate_session_success_rate(self) -> float:
        """Calculate overall session success rate."""
        if not self._completed_sessions:
            return 100.0
        
        total_searches = sum(s.total_searches for s in self._completed_sessions)
        successful_searches = sum(s.successful_searches for s in self._completed_sessions)
        
        return (successful_searches / total_searches * 100) if total_searches > 0 else 100.0
    
    def _calculate_bounce_rate(self) -> float:
        """Calculate bounce rate (sessions with only one search)."""
        if not self._completed_sessions:
            return 0.0
        
        single_search_sessions = sum(
            1 for s in self._completed_sessions if s.total_searches == 1
        )
        
        return (single_search_sessions / len(self._completed_sessions) * 100)
    
    def _generate_quality_recommendations(self) -> List[str]:
        """Generate recommendations based on search quality analysis."""
        recommendations = []
        
        # Check zero result rate
        total_queries = sum(p.frequency for p in self._query_patterns.values())
        if total_queries > 0:
            zero_result_rate = len(self._zero_result_queries) / total_queries * 100
            if zero_result_rate > 10:
                recommendations.append(
                    f"High zero-result rate ({zero_result_rate:.1f}%). "
                    "Consider reviewing content coverage or query processing."
                )
        
        # Check slow query rate
        if self._slow_queries:
            slow_rate = len(self._slow_queries) / total_queries * 100 if total_queries > 0 else 0
            if slow_rate > 5:
                recommendations.append(
                    f"High slow query rate ({slow_rate:.1f}%). "
                    "Consider optimizing search performance or scaling resources."
                )
        
        # Check failure rate
        if self._failed_queries:
            failure_rate = len(self._failed_queries) / total_queries * 100 if total_queries > 0 else 0
            if failure_rate > 1:
                recommendations.append(
                    f"Elevated failure rate ({failure_rate:.1f}%). "
                    "Review error logs and system stability."
                )
        
        return recommendations
    
    def _contains_thai(self, text: str) -> bool:
        """Check if text contains Thai characters."""
        thai_range = range(0x0E00, 0x0E7F)
        return any(ord(char) in thai_range for char in text)
    
    def _contains_english(self, text: str) -> bool:
        """Check if text contains English characters."""
        return any(char.isalpha() and char.isascii() for char in text)
    
    def _start_background_tasks(self) -> None:
        """Start background tasks for periodic processing."""
        # TODO: Implement periodic trend calculation
        # TODO: Implement periodic data cleanup
        # TODO: Implement periodic export
        pass


# Global analytics collector instance
analytics_collector = SearchAnalyticsCollector()