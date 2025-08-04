#!/bin/bash

# Thai Search Proxy Monitoring Script for NPM Deployment
# This script helps monitor the search proxy service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.npm-search-proxy.yml"
ENV_FILE=".env"

# Get port from env file
PORT=$(grep -E "^THAI_TOKENIZER_PORT=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2 || echo "8000")
BASE_URL="http://localhost:${PORT}"

echo -e "${BLUE}Thai Search Proxy Monitor${NC}"
echo "========================="

# Function to check service status
check_status() {
    echo -e "\n${YELLOW}Service Status${NC}"
    echo "--------------"
    
    # Check if container is running
    if docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
        echo -e "Container: ${GREEN}Running${NC}"
        
        # Get container stats
        CONTAINER_NAME=$(docker-compose -f "$COMPOSE_FILE" ps -q)
        if [ ! -z "$CONTAINER_NAME" ]; then
            echo -e "\nContainer Statistics:"
            docker stats --no-stream "$CONTAINER_NAME" | tail -n +2
        fi
    else
        echo -e "Container: ${RED}Not Running${NC}"
        return 1
    fi
}

# Function to check health
check_health() {
    echo -e "\n${YELLOW}Health Checks${NC}"
    echo "-------------"
    
    # Basic health check
    if curl -f -s "${BASE_URL}/health" > /dev/null; then
        echo -e "Basic Health: ${GREEN}OK${NC}"
    else
        echo -e "Basic Health: ${RED}FAILED${NC}"
    fi
    
    # API health check
    API_HEALTH=$(curl -s "${BASE_URL}/api/v1/health" 2>/dev/null)
    if echo "$API_HEALTH" | grep -q '"status":"healthy"'; then
        echo -e "API Health: ${GREEN}OK${NC}"
        
        # Extract metrics from health check
        if command -v jq &> /dev/null; then
            TOTAL_SEARCHES=$(echo "$API_HEALTH" | jq -r '.metrics.total_searches // 0')
            SUCCESS_RATE=$(echo "$API_HEALTH" | jq -r '.metrics.success_rate_percent // 0')
            AVG_RESPONSE=$(echo "$API_HEALTH" | jq -r '.metrics.avg_response_time_ms // 0')
            
            echo -e "\nQuick Metrics:"
            echo "  Total Searches: $TOTAL_SEARCHES"
            echo "  Success Rate: ${SUCCESS_RATE}%"
            echo "  Avg Response Time: ${AVG_RESPONSE}ms"
        fi
    else
        echo -e "API Health: ${RED}FAILED${NC}"
    fi
}

# Function to show recent logs
show_logs() {
    echo -e "\n${YELLOW}Recent Logs (last 20 lines)${NC}"
    echo "---------------------------"
    docker-compose -f "$COMPOSE_FILE" logs --tail=20 2>/dev/null || echo "No logs available"
}

# Function to check search metrics
check_metrics() {
    echo -e "\n${YELLOW}Search Proxy Metrics${NC}"
    echo "-------------------"
    
    METRICS=$(curl -s "${BASE_URL}/metrics/search-proxy" 2>/dev/null)
    if [ ! -z "$METRICS" ]; then
        # Extract key metrics
        echo "$METRICS" | grep -E "search_proxy_total_searches|search_proxy_success_rate|search_proxy_response_time_p95" | head -10
    else
        echo "Metrics not available"
    fi
}

# Function to check analytics
check_analytics() {
    echo -e "\n${YELLOW}Search Analytics Summary${NC}"
    echo "-----------------------"
    
    ANALYTICS=$(curl -s "${BASE_URL}/api/v1/analytics/queries" 2>/dev/null)
    if [ ! -z "$ANALYTICS" ] && command -v jq &> /dev/null; then
        TOTAL_UNIQUE=$(echo "$ANALYTICS" | jq -r '.total_unique_queries // 0')
        TOTAL_VOLUME=$(echo "$ANALYTICS" | jq -r '.total_query_volume // 0')
        
        echo "Total Unique Queries: $TOTAL_UNIQUE"
        echo "Total Query Volume: $TOTAL_VOLUME"
        
        # Show top queries if available
        echo -e "\nTop 5 Queries:"
        echo "$ANALYTICS" | jq -r '.top_queries[:5] | .[] | "  - \(.query) (count: \(.frequency))"' 2>/dev/null || echo "  No data available"
    else
        echo "Analytics not available"
    fi
}

# Function to test search functionality
test_search() {
    echo -e "\n${YELLOW}Search Functionality Test${NC}"
    echo "------------------------"
    
    # Test with Thai query
    echo "Testing Thai search..."
    RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/search" \
        -H "Content-Type: application/json" \
        -d '{"query":"ทดสอบ","index_name":"documents"}' 2>/dev/null)
    
    if echo "$RESPONSE" | grep -q '"hits"'; then
        echo -e "Thai Search: ${GREEN}Working${NC}"
        if command -v jq &> /dev/null; then
            HITS=$(echo "$RESPONSE" | jq -r '.total_hits // 0')
            PROCESS_TIME=$(echo "$RESPONSE" | jq -r '.processing_time_ms // 0')
            echo "  Results: $HITS hits in ${PROCESS_TIME}ms"
        fi
    else
        echo -e "Thai Search: ${RED}Failed${NC}"
    fi
}

# Function to show resource usage
show_resources() {
    echo -e "\n${YELLOW}Resource Usage${NC}"
    echo "--------------"
    
    # Get container name
    CONTAINER_NAME=$(docker-compose -f "$COMPOSE_FILE" ps -q)
    if [ ! -z "$CONTAINER_NAME" ]; then
        # CPU and Memory usage
        docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" "$CONTAINER_NAME"
        
        # Disk usage for volumes
        echo -e "\nVolume Usage:"
        docker volume ls | grep -E "search_analytics|search_logs|search_cache" | while read -r line; do
            VOLUME_NAME=$(echo "$line" | awk '{print $2}')
            SIZE=$(docker run --rm -v "$VOLUME_NAME:/data" alpine du -sh /data 2>/dev/null | cut -f1)
            echo "  $VOLUME_NAME: $SIZE"
        done
    fi
}

# Function to continuous monitoring
continuous_monitor() {
    echo -e "\n${YELLOW}Starting continuous monitoring (Ctrl+C to stop)...${NC}\n"
    
    while true; do
        clear
        echo -e "${BLUE}Thai Search Proxy Monitor - $(date)${NC}"
        echo "================================================"
        
        check_status
        check_health
        check_metrics
        
        echo -e "\n${YELLOW}Refreshing in 30 seconds...${NC}"
        sleep 30
    done
}

# Main menu
show_menu() {
    echo -e "\n${YELLOW}Monitoring Options${NC}"
    echo "=================="
    echo "1. Quick Status Check"
    echo "2. View Recent Logs"
    echo "3. Search Analytics"
    echo "4. Test Search Function"
    echo "5. Resource Usage"
    echo "6. Continuous Monitoring"
    echo "7. Export Metrics"
    echo "8. Exit"
}

# Export metrics function
export_metrics() {
    echo -e "\n${YELLOW}Exporting Metrics${NC}"
    echo "-----------------"
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    EXPORT_DIR="metrics_export_${TIMESTAMP}"
    mkdir -p "$EXPORT_DIR"
    
    # Export different metric types
    curl -s "${BASE_URL}/metrics" > "$EXPORT_DIR/all_metrics.txt"
    curl -s "${BASE_URL}/metrics/search-proxy" > "$EXPORT_DIR/search_proxy_metrics.txt"
    curl -s "${BASE_URL}/api/v1/analytics/queries" > "$EXPORT_DIR/query_analytics.json"
    curl -s "${BASE_URL}/api/v1/analytics/quality-report" > "$EXPORT_DIR/quality_report.json"
    
    echo -e "${GREEN}Metrics exported to $EXPORT_DIR/${NC}"
}

# Main loop
main() {
    while true; do
        show_menu
        read -p "Select option (1-8): " choice
        
        case $choice in
            1)
                check_status
                check_health
                ;;
            2)
                show_logs
                ;;
            3)
                check_analytics
                ;;
            4)
                test_search
                ;;
            5)
                show_resources
                ;;
            6)
                continuous_monitor
                ;;
            7)
                export_metrics
                ;;
            8)
                echo -e "${GREEN}Exiting monitor${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid option${NC}"
                ;;
        esac
        
        echo -e "\n${YELLOW}Press Enter to continue...${NC}"
        read
    done
}

# Run main function
main