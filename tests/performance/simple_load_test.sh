#!/bin/bash

# Simple load test for Thai Search Proxy
# Uses curl and parallel processing

echo "Thai Search Proxy Simple Load Test"
echo "=================================="

# Configuration
BASE_URL="${BASE_URL:-http://localhost:8000}"
REQUESTS="${REQUESTS:-100}"
CONCURRENCY="${CONCURRENCY:-10}"

# Test queries
QUERIES=(
    "ข้าว"
    "มะพร้าว"
    "สาหร่าย"
    "สาหร่ายวากาเมะ"
    "การเกษตรแบบยั่งยืน"
    "เทคโนโลยีการเพาะปลูก"
    "น้ำมันมะพร้าวบริสุทธิ์"
    "Smart Farm"
)

# Create temporary file for results
RESULTS_FILE=$(mktemp)

# Function to make a single request
make_request() {
    local query_index=$((RANDOM % ${#QUERIES[@]}))
    local query="${QUERIES[$query_index]}"
    local start_time=$(date +%s.%N)
    
    response=$(curl -s -w "\n%{http_code}\n%{time_total}" -X POST "${BASE_URL}/api/v1/search" \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"${query}\", \"index_name\": \"research\", \"options\": {\"limit\": 10}}" 2>/dev/null)
    
    local end_time=$(date +%s.%N)
    local http_code=$(echo "$response" | tail -2 | head -1)
    local response_time=$(echo "$response" | tail -1)
    
    echo "${http_code},${response_time}" >> "$RESULTS_FILE"
}

export -f make_request
export BASE_URL RESULTS_FILE
export QUERIES

echo "Starting load test..."
echo "- URL: $BASE_URL"
echo "- Requests: $REQUESTS"
echo "- Concurrency: $CONCURRENCY"
echo ""

# Run requests in parallel
START_TIME=$(date +%s)
seq 1 "$REQUESTS" | xargs -P "$CONCURRENCY" -I {} bash -c 'make_request'
END_TIME=$(date +%s)

DURATION=$((END_TIME - START_TIME))

# Analyze results
echo ""
echo "Results:"
echo "--------"

# Count success/failures
SUCCESS=$(grep "^200," "$RESULTS_FILE" | wc -l)
FAILED=$((REQUESTS - SUCCESS))
SUCCESS_RATE=$(echo "scale=2; $SUCCESS * 100 / $REQUESTS" | bc)

echo "Total Requests: $REQUESTS"
echo "Successful: $SUCCESS"
echo "Failed: $FAILED"
echo "Success Rate: ${SUCCESS_RATE}%"
echo "Total Duration: ${DURATION}s"
echo "Requests/sec: $(echo "scale=2; $REQUESTS / $DURATION" | bc)"

# Response time analysis
if [ "$SUCCESS" -gt 0 ]; then
    echo ""
    echo "Response Times (successful requests):"
    
    # Extract response times for successful requests
    grep "^200," "$RESULTS_FILE" | cut -d',' -f2 | sort -n > "${RESULTS_FILE}.times"
    
    MIN=$(head -1 "${RESULTS_FILE}.times")
    MAX=$(tail -1 "${RESULTS_FILE}.times")
    
    # Calculate average
    AVG=$(awk '{sum+=$1} END {printf "%.3f", sum/NR}' "${RESULTS_FILE}.times")
    
    # Calculate median
    COUNT=$(wc -l < "${RESULTS_FILE}.times")
    MEDIAN_LINE=$((COUNT / 2))
    MEDIAN=$(sed -n "${MEDIAN_LINE}p" "${RESULTS_FILE}.times")
    
    # Calculate 95th percentile
    P95_LINE=$((COUNT * 95 / 100))
    P95=$(sed -n "${P95_LINE}p" "${RESULTS_FILE}.times")
    
    echo "  Min: ${MIN}s"
    echo "  Max: ${MAX}s"
    echo "  Average: ${AVG}s"
    echo "  Median: ${MEDIAN}s"
    echo "  95th percentile: ${P95}s"
    
    rm "${RESULTS_FILE}.times"
fi

# Cleanup
rm "$RESULTS_FILE"

echo ""
echo "Load test completed!"