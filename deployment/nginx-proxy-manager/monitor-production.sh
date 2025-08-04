#!/bin/bash

# Thai Search Proxy Production Monitoring Script
# Monitors the health and performance of the service

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SERVICE_URL="${SERVICE_URL:-http://localhost:8000}"
CHECK_INTERVAL="${CHECK_INTERVAL:-60}" # seconds

# Clear screen
clear

echo "===================================="
echo "Thai Search Proxy Production Monitor"
echo "===================================="
echo ""

# Function to format uptime
format_uptime() {
    local total_seconds=$1
    local days=$((total_seconds / 86400))
    local hours=$(((total_seconds % 86400) / 3600))
    local minutes=$(((total_seconds % 3600) / 60))
    
    if [ $days -gt 0 ]; then
        echo "${days}d ${hours}h ${minutes}m"
    elif [ $hours -gt 0 ]; then
        echo "${hours}h ${minutes}m"
    else
        echo "${minutes}m"
    fi
}

# Main monitoring loop
while true; do
    # Clear previous output
    printf "\033[8;0H"
    
    # Get current time
    echo -e "${BLUE}Last checked: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
    echo ""
    
    # Check health status
    echo -e "${YELLOW}Health Status:${NC}"
    if health_response=$(curl -s "${SERVICE_URL}/health" 2>/dev/null); then
        status=$(echo "$health_response" | jq -r '.status // "unknown"')
        
        if [ "$status" = "healthy" ]; then
            echo -e "  Status: ${GREEN}●${NC} Healthy"
            
            # Extract health details
            uptime=$(echo "$health_response" | jq -r '.uptime_seconds // 0')
            echo -e "  Uptime: $(format_uptime $uptime)"
            
            # Check dependencies
            meilisearch_status=$(echo "$health_response" | jq -r '.dependencies.meilisearch // "unknown"')
            if [ "$meilisearch_status" = "healthy" ]; then
                echo -e "  MeiliSearch: ${GREEN}●${NC} Connected"
            else
                echo -e "  MeiliSearch: ${RED}●${NC} Disconnected"
            fi
        else
            echo -e "  Status: ${RED}●${NC} Unhealthy"
        fi
    else
        echo -e "  Status: ${RED}●${NC} Service Unreachable"
    fi
    
    echo ""
    
    # Get metrics
    echo -e "${YELLOW}Performance Metrics:${NC}"
    if metrics_response=$(curl -s "${SERVICE_URL}/api/v1/metrics/summary" 2>/dev/null); then
        # Search metrics
        total_searches=$(echo "$metrics_response" | jq -r '.search_metrics.total_searches // 0')
        success_rate=$(echo "$metrics_response" | jq -r '.search_metrics.success_rate_percent // 0')
        avg_response_time=$(echo "$metrics_response" | jq -r '.search_metrics.avg_response_time_ms // 0')
        
        echo -e "  Total Searches: ${total_searches}"
        echo -e "  Success Rate: ${success_rate}%"
        printf "  Avg Response Time: %.2fms\n" "$avg_response_time"
        
        # Active searches
        active_searches=$(echo "$metrics_response" | jq -r '.performance_metrics.active_searches // 0')
        echo -e "  Active Searches: ${active_searches}"
        
        # Cache hit rate
        cache_hit_rate=$(echo "$metrics_response" | jq -r '.search_metrics.cache_hit_rate_percent // 0')
        echo -e "  Cache Hit Rate: ${cache_hit_rate}%"
    else
        echo -e "  ${RED}Unable to fetch metrics${NC}"
    fi
    
    echo ""
    
    # Container stats
    echo -e "${YELLOW}Container Resources:${NC}"
    container_name="thai_search_proxy_npm-thai-tokenizer-search-proxy-1"
    if stats=$(docker stats --no-stream --format "json" "$container_name" 2>/dev/null); then
        cpu_usage=$(echo "$stats" | jq -r '.CPUPerc' | sed 's/%//')
        mem_usage=$(echo "$stats" | jq -r '.MemUsage' | awk '{print $1}')
        mem_limit=$(echo "$stats" | jq -r '.MemUsage' | awk '{print $3}')
        
        echo -e "  CPU Usage: ${cpu_usage}%"
        echo -e "  Memory: ${mem_usage} / ${mem_limit}"
    else
        echo -e "  ${RED}Container not found${NC}"
    fi
    
    echo ""
    
    # Recent errors (from logs)
    echo -e "${YELLOW}Recent Activity:${NC}"
    if recent_logs=$(docker logs --tail 5 --since 1m "$container_name" 2>&1 | grep -E "(ERROR|WARNING)" | tail -3); then
        if [ -n "$recent_logs" ]; then
            echo "$recent_logs" | while IFS= read -r line; do
                if [[ $line == *"ERROR"* ]]; then
                    echo -e "  ${RED}[ERROR]${NC} ${line##*ERROR}"
                else
                    echo -e "  ${YELLOW}[WARN]${NC} ${line##*WARNING}"
                fi
            done
        else
            echo -e "  ${GREEN}No recent errors or warnings${NC}"
        fi
    fi
    
    echo ""
    echo "---"
    echo "Press Ctrl+C to exit"
    echo "Refreshing every ${CHECK_INTERVAL} seconds..."
    
    # Wait before next check
    sleep "$CHECK_INTERVAL"
done