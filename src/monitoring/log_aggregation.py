"""Log aggregation and analysis utilities for monitoring integration."""

import json
import re
import time
from typing import Dict, Any, List, Optional, Iterator, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
import gzip

from src.utils.logging import get_structured_logger

logger = get_structured_logger(__name__)


@dataclass
class LogEntry:
    """Structured log entry."""
    timestamp: datetime
    level: str
    service: str
    logger: str
    message: str
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None
    error_type: Optional[str] = None
    processing_time_ms: Optional[float] = None
    event_type: Optional[str] = None
    raw_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.raw_data is None:
            self.raw_data = {}


@dataclass
class LogAnalysisResult:
    """Result of log analysis."""
    time_range: Tuple[datetime, datetime]
    total_entries: int
    entries_by_level: Dict[str, int]
    error_patterns: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]
    top_errors: List[Dict[str, Any]]
    request_patterns: Dict[str, Any]
    recommendations: List[str]


class LogAggregator:
    """Aggregates and processes log files for monitoring systems."""
    
    def __init__(self, log_directory: str = "/var/log/thai-tokenizer"):
        self.log_directory = Path(log_directory)
        self.supported_formats = ["json", "text"]
        self.max_file_size_mb = 100
        self.max_entries_per_file = 100000
    
    def read_log_files(self, 
                      hours_back: int = 24,
                      log_types: List[str] = None,
                      include_compressed: bool = True) -> Iterator[LogEntry]:
        """Read log files and yield structured log entries."""
        if log_types is None:
            log_types = ["app", "performance", "errors", "metrics"]
        
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        for log_type in log_types:
            log_files = self._get_log_files(log_type, include_compressed)
            
            for log_file in log_files:
                try:
                    # Check file modification time
                    if log_file.stat().st_mtime < cutoff_time.timestamp():
                        continue
                    
                    # Check file size
                    file_size_mb = log_file.stat().st_size / (1024 * 1024)
                    if file_size_mb > self.max_file_size_mb:
                        logger.warning("Large log file detected", 
                                     file_path=str(log_file), 
                                     size_mb=file_size_mb)
                    
                    # Read entries from file
                    yield from self._read_log_file(log_file, cutoff_time)
                    
                except Exception as e:
                    logger.error("Failed to read log file", 
                               file_path=str(log_file), error=e)
    
    def _get_log_files(self, log_type: str, include_compressed: bool) -> List[Path]:
        """Get list of log files for a specific type."""
        log_files = []
        
        if not self.log_directory.exists():
            logger.warning("Log directory does not exist", 
                          directory=str(self.log_directory))
            return log_files
        
        # Current log file
        current_file = self.log_directory / f"{log_type}.log"
        if current_file.exists():
            log_files.append(current_file)
        
        if include_compressed:
            # Rotated log files
            pattern = f"{log_type}.log.*"
            for file_path in self.log_directory.glob(pattern):
                log_files.append(file_path)
        
        # Sort by modification time (newest first)
        log_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        return log_files
    
    def _read_log_file(self, file_path: Path, cutoff_time: datetime) -> Iterator[LogEntry]:
        """Read entries from a single log file."""
        entry_count = 0
        
        try:
            # Determine if file is compressed
            if file_path.suffix == '.gz':
                file_handle = gzip.open(file_path, 'rt', encoding='utf-8')
            else:
                file_handle = open(file_path, 'r', encoding='utf-8')
            
            with file_handle as f:
                for line_num, line in enumerate(f, 1):
                    if entry_count >= self.max_entries_per_file:
                        logger.warning("Max entries per file reached", 
                                     file_path=str(file_path),
                                     max_entries=self.max_entries_per_file)
                        break
                    
                    try:
                        entry = self._parse_log_line(line.strip())
                        if entry and entry.timestamp >= cutoff_time:
                            yield entry
                            entry_count += 1
                    except Exception as e:
                        logger.debug("Failed to parse log line", 
                                   file_path=str(file_path),
                                   line_num=line_num,
                                   error=e)
                        
        except Exception as e:
            logger.error("Failed to read log file", 
                        file_path=str(file_path), error=e)
    
    def _parse_log_line(self, line: str) -> Optional[LogEntry]:
        """Parse a single log line into a LogEntry."""
        if not line.strip():
            return None
        
        try:
            # Try JSON format first
            data = json.loads(line)
            
            # Parse timestamp
            timestamp_str = data.get("timestamp", "")
            if timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                timestamp = datetime.now()
            
            return LogEntry(
                timestamp=timestamp,
                level=data.get("level", "INFO"),
                service=data.get("service", "unknown"),
                logger=data.get("logger", "unknown"),
                message=data.get("message", ""),
                correlation_id=data.get("correlation_id"),
                request_id=data.get("request_id"),
                error_type=data.get("error_type"),
                processing_time_ms=data.get("processing_time_ms"),
                event_type=data.get("event_type"),
                raw_data=data
            )
            
        except json.JSONDecodeError:
            # Try text format parsing
            return self._parse_text_log_line(line)
    
    def _parse_text_log_line(self, line: str) -> Optional[LogEntry]:
        """Parse text format log line."""
        # Basic text log parsing - adjust regex based on your log format
        patterns = [
            # Standard format: TIMESTAMP LEVEL LOGGER MESSAGE
            r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)\s+(\w+)\s+(\S+)\s+(.+)',
            # Simple format: LEVEL MESSAGE
            r'(\w+):\s*(.+)'
        ]
        
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                if len(match.groups()) == 4:
                    timestamp_str, level, logger_name, message = match.groups()
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    except:
                        timestamp = datetime.now()
                else:
                    level, message = match.groups()
                    timestamp = datetime.now()
                    logger_name = "unknown"
                
                return LogEntry(
                    timestamp=timestamp,
                    level=level,
                    service="thai-tokenizer",
                    logger=logger_name,
                    message=message,
                    raw_data={"raw_line": line}
                )
        
        return None
    
    def aggregate_logs(self, 
                      hours_back: int = 24,
                      log_types: List[str] = None) -> Dict[str, Any]:
        """Aggregate log data for monitoring dashboards."""
        entries = list(self.read_log_files(hours_back, log_types))
        
        if not entries:
            return {
                "total_entries": 0,
                "time_range": [datetime.now().isoformat(), datetime.now().isoformat()],
                "entries_by_level": {},
                "entries_by_hour": {},
                "error_summary": {},
                "performance_summary": {}
            }
        
        # Sort entries by timestamp
        entries.sort(key=lambda e: e.timestamp)
        
        # Basic aggregations
        total_entries = len(entries)
        time_range = [entries[0].timestamp.isoformat(), entries[-1].timestamp.isoformat()]
        
        # Count by log level
        entries_by_level = Counter(entry.level for entry in entries)
        
        # Count by hour
        entries_by_hour = defaultdict(int)
        for entry in entries:
            hour_key = entry.timestamp.strftime("%Y-%m-%d %H:00")
            entries_by_hour[hour_key] += 1
        
        # Error analysis
        error_entries = [e for e in entries if e.level in ["ERROR", "CRITICAL"]]
        error_types = Counter(e.error_type for e in error_entries if e.error_type)
        error_messages = Counter(e.message for e in error_entries)
        
        # Performance analysis
        perf_entries = [e for e in entries if e.processing_time_ms is not None]
        if perf_entries:
            processing_times = [e.processing_time_ms for e in perf_entries]
            avg_processing_time = sum(processing_times) / len(processing_times)
            max_processing_time = max(processing_times)
            min_processing_time = min(processing_times)
        else:
            avg_processing_time = max_processing_time = min_processing_time = 0
        
        return {
            "total_entries": total_entries,
            "time_range": time_range,
            "entries_by_level": dict(entries_by_level),
            "entries_by_hour": dict(entries_by_hour),
            "error_summary": {
                "total_errors": len(error_entries),
                "error_types": dict(error_types.most_common(10)),
                "top_error_messages": dict(error_messages.most_common(5))
            },
            "performance_summary": {
                "total_performance_entries": len(perf_entries),
                "avg_processing_time_ms": avg_processing_time,
                "max_processing_time_ms": max_processing_time,
                "min_processing_time_ms": min_processing_time
            }
        }
    
    def export_for_elasticsearch(self, 
                                hours_back: int = 24,
                                batch_size: int = 1000) -> Iterator[List[Dict[str, Any]]]:
        """Export log entries in Elasticsearch bulk format."""
        batch = []
        
        for entry in self.read_log_files(hours_back):
            # Create Elasticsearch document
            doc = {
                "@timestamp": entry.timestamp.isoformat(),
                "level": entry.level,
                "service": entry.service,
                "logger": entry.logger,
                "message": entry.message,
                "correlation_id": entry.correlation_id,
                "request_id": entry.request_id,
                "error_type": entry.error_type,
                "processing_time_ms": entry.processing_time_ms,
                "event_type": entry.event_type,
                **entry.raw_data
            }
            
            # Add index metadata
            index_name = f"thai-tokenizer-logs-{entry.timestamp.strftime('%Y.%m.%d')}"
            batch.append({"index": {"_index": index_name}})
            batch.append(doc)
            
            if len(batch) >= batch_size * 2:  # *2 because each entry has metadata + doc
                yield batch
                batch = []
        
        if batch:
            yield batch
    
    def export_for_splunk(self, hours_back: int = 24) -> Iterator[str]:
        """Export log entries in Splunk format."""
        for entry in self.read_log_files(hours_back):
            # Create Splunk event
            event_data = {
                "timestamp": entry.timestamp.isoformat(),
                "level": entry.level,
                "service": entry.service,
                "logger": entry.logger,
                "message": entry.message,
                "correlation_id": entry.correlation_id,
                "request_id": entry.request_id,
                "error_type": entry.error_type,
                "processing_time_ms": entry.processing_time_ms,
                "event_type": entry.event_type,
                **entry.raw_data
            }
            
            yield json.dumps(event_data)


class LogAnalyzer:
    """Analyzes log patterns and provides insights for monitoring."""
    
    def __init__(self, log_aggregator: LogAggregator):
        self.log_aggregator = log_aggregator
        self.error_patterns = [
            {
                "name": "connection_timeout",
                "pattern": r"(?i)timeout|connection.*timeout|read.*timeout",
                "severity": "high",
                "category": "connectivity"
            },
            {
                "name": "memory_error",
                "pattern": r"(?i)memory|out of memory|oom|memory.*error",
                "severity": "critical",
                "category": "resource"
            },
            {
                "name": "tokenization_failure",
                "pattern": r"(?i)tokeniz.*fail|segment.*fail|thai.*fail",
                "severity": "high",
                "category": "functionality"
            },
            {
                "name": "meilisearch_error",
                "pattern": r"(?i)meilisearch|meili.*error|search.*error",
                "severity": "high",
                "category": "dependency"
            },
            {
                "name": "authentication_error",
                "pattern": r"(?i)auth.*fail|unauthorized|forbidden|401|403",
                "severity": "medium",
                "category": "security"
            }
        ]
    
    def analyze_logs(self, hours_back: int = 24) -> LogAnalysisResult:
        """Perform comprehensive log analysis."""
        entries = list(self.log_aggregator.read_log_files(hours_back))
        
        if not entries:
            return LogAnalysisResult(
                time_range=(datetime.now(), datetime.now()),
                total_entries=0,
                entries_by_level={},
                error_patterns=[],
                performance_metrics={},
                top_errors=[],
                request_patterns={},
                recommendations=[]
            )
        
        # Sort entries by timestamp
        entries.sort(key=lambda e: e.timestamp)
        time_range = (entries[0].timestamp, entries[-1].timestamp)
        
        # Basic statistics
        total_entries = len(entries)
        entries_by_level = Counter(entry.level for entry in entries)
        
        # Error pattern analysis
        error_patterns = self._analyze_error_patterns(entries)
        
        # Performance analysis
        performance_metrics = self._analyze_performance(entries)
        
        # Top errors
        top_errors = self._get_top_errors(entries)
        
        # Request pattern analysis
        request_patterns = self._analyze_request_patterns(entries)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            entries, error_patterns, performance_metrics
        )
        
        return LogAnalysisResult(
            time_range=time_range,
            total_entries=total_entries,
            entries_by_level=dict(entries_by_level),
            error_patterns=error_patterns,
            performance_metrics=performance_metrics,
            top_errors=top_errors,
            request_patterns=request_patterns,
            recommendations=recommendations
        )
    
    def _analyze_error_patterns(self, entries: List[LogEntry]) -> List[Dict[str, Any]]:
        """Analyze error patterns in log entries."""
        error_entries = [e for e in entries if e.level in ["ERROR", "CRITICAL"]]
        pattern_matches = []
        
        for pattern_config in self.error_patterns:
            pattern = re.compile(pattern_config["pattern"])
            matches = []
            
            for entry in error_entries:
                if pattern.search(entry.message):
                    matches.append({
                        "timestamp": entry.timestamp.isoformat(),
                        "message": entry.message,
                        "correlation_id": entry.correlation_id
                    })
            
            if matches:
                pattern_matches.append({
                    "name": pattern_config["name"],
                    "severity": pattern_config["severity"],
                    "category": pattern_config["category"],
                    "count": len(matches),
                    "recent_matches": matches[-5:],  # Last 5 matches
                    "first_occurrence": matches[0]["timestamp"],
                    "last_occurrence": matches[-1]["timestamp"]
                })
        
        return sorted(pattern_matches, key=lambda x: x["count"], reverse=True)
    
    def _analyze_performance(self, entries: List[LogEntry]) -> Dict[str, Any]:
        """Analyze performance metrics from log entries."""
        perf_entries = [e for e in entries if e.processing_time_ms is not None]
        
        if not perf_entries:
            return {
                "total_requests": 0,
                "avg_response_time_ms": 0,
                "p95_response_time_ms": 0,
                "p99_response_time_ms": 0,
                "slow_requests": []
            }
        
        processing_times = [e.processing_time_ms for e in perf_entries]
        processing_times.sort()
        
        total_requests = len(perf_entries)
        avg_response_time = sum(processing_times) / len(processing_times)
        
        # Calculate percentiles
        p95_index = int(0.95 * len(processing_times))
        p99_index = int(0.99 * len(processing_times))
        p95_response_time = processing_times[p95_index] if p95_index < len(processing_times) else processing_times[-1]
        p99_response_time = processing_times[p99_index] if p99_index < len(processing_times) else processing_times[-1]
        
        # Find slow requests (above 95th percentile)
        slow_threshold = p95_response_time
        slow_requests = [
            {
                "timestamp": e.timestamp.isoformat(),
                "processing_time_ms": e.processing_time_ms,
                "message": e.message,
                "correlation_id": e.correlation_id
            }
            for e in perf_entries
            if e.processing_time_ms >= slow_threshold
        ]
        
        return {
            "total_requests": total_requests,
            "avg_response_time_ms": avg_response_time,
            "p95_response_time_ms": p95_response_time,
            "p99_response_time_ms": p99_response_time,
            "slow_requests": slow_requests[-10:]  # Last 10 slow requests
        }
    
    def _get_top_errors(self, entries: List[LogEntry]) -> List[Dict[str, Any]]:
        """Get top error messages by frequency."""
        error_entries = [e for e in entries if e.level in ["ERROR", "CRITICAL"]]
        error_counter = Counter()
        error_details = {}
        
        for entry in error_entries:
            # Normalize error message (remove specific values)
            normalized_message = self._normalize_error_message(entry.message)
            error_counter[normalized_message] += 1
            
            if normalized_message not in error_details:
                error_details[normalized_message] = {
                    "first_occurrence": entry.timestamp,
                    "last_occurrence": entry.timestamp,
                    "error_type": entry.error_type,
                    "sample_correlation_ids": []
                }
            else:
                error_details[normalized_message]["last_occurrence"] = entry.timestamp
            
            # Collect sample correlation IDs
            if entry.correlation_id and len(error_details[normalized_message]["sample_correlation_ids"]) < 5:
                error_details[normalized_message]["sample_correlation_ids"].append(entry.correlation_id)
        
        top_errors = []
        for message, count in error_counter.most_common(10):
            details = error_details[message]
            top_errors.append({
                "message": message,
                "count": count,
                "error_type": details["error_type"],
                "first_occurrence": details["first_occurrence"].isoformat(),
                "last_occurrence": details["last_occurrence"].isoformat(),
                "sample_correlation_ids": details["sample_correlation_ids"]
            })
        
        return top_errors
    
    def _normalize_error_message(self, message: str) -> str:
        """Normalize error message by removing specific values."""
        # Remove timestamps
        message = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?', 'TIMESTAMP', message)
        
        # Remove numbers that might be IDs or values
        message = re.sub(r'\b\d+\b', 'NUMBER', message)
        
        # Remove UUIDs
        message = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', 'UUID', message)
        
        # Remove file paths
        message = re.sub(r'/[^\s]+', 'PATH', message)
        
        return message
    
    def _analyze_request_patterns(self, entries: List[LogEntry]) -> Dict[str, Any]:
        """Analyze request patterns and trends."""
        request_entries = [e for e in entries if e.correlation_id]
        
        if not request_entries:
            return {
                "total_requests": 0,
                "unique_requests": 0,
                "requests_per_hour": {},
                "avg_requests_per_hour": 0
            }
        
        # Count requests by correlation ID
        correlation_ids = set(e.correlation_id for e in request_entries)
        unique_requests = len(correlation_ids)
        
        # Count requests by hour
        requests_per_hour = defaultdict(int)
        for entry in request_entries:
            hour_key = entry.timestamp.strftime("%Y-%m-%d %H:00")
            requests_per_hour[hour_key] += 1
        
        avg_requests_per_hour = sum(requests_per_hour.values()) / len(requests_per_hour) if requests_per_hour else 0
        
        return {
            "total_requests": len(request_entries),
            "unique_requests": unique_requests,
            "requests_per_hour": dict(requests_per_hour),
            "avg_requests_per_hour": avg_requests_per_hour
        }
    
    def _generate_recommendations(self, 
                                entries: List[LogEntry],
                                error_patterns: List[Dict[str, Any]],
                                performance_metrics: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on log analysis."""
        recommendations = []
        
        # Error-based recommendations
        for pattern in error_patterns:
            if pattern["count"] > 10:
                if pattern["category"] == "connectivity":
                    recommendations.append(
                        f"High number of {pattern['name']} errors ({pattern['count']}). "
                        "Consider increasing timeout values or checking network connectivity."
                    )
                elif pattern["category"] == "resource":
                    recommendations.append(
                        f"Resource-related errors detected ({pattern['count']} {pattern['name']} errors). "
                        "Consider increasing memory limits or optimizing resource usage."
                    )
                elif pattern["category"] == "functionality":
                    recommendations.append(
                        f"Functionality errors detected ({pattern['count']} {pattern['name']} errors). "
                        "Check tokenizer configuration and Thai language model availability."
                    )
        
        # Performance-based recommendations
        if performance_metrics.get("avg_response_time_ms", 0) > 1000:
            recommendations.append(
                f"High average response time ({performance_metrics['avg_response_time_ms']:.1f}ms). "
                "Consider optimizing tokenization algorithms or increasing system resources."
            )
        
        if performance_metrics.get("p99_response_time_ms", 0) > 5000:
            recommendations.append(
                f"Very high P99 response time ({performance_metrics['p99_response_time_ms']:.1f}ms). "
                "Investigate slow requests and consider implementing request timeouts."
            )
        
        # Log level recommendations
        error_entries = [e for e in entries if e.level in ["ERROR", "CRITICAL"]]
        if len(error_entries) > len(entries) * 0.05:  # More than 5% errors
            recommendations.append(
                f"High error rate detected ({len(error_entries)} errors out of {len(entries)} total entries). "
                "Investigate root causes and implement error handling improvements."
            )
        
        return recommendations