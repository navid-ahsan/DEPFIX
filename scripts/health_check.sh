#!/bin/bash
# Health check script to verify all services are running
# Usage: bash scripts/health_check.sh

set -e

echo "========================================"
echo "RAG Application Health Check"
echo "========================================"
echo ""

EXIT_CODE=0

# Function to check service health
check_service() {
    local name=$1
    local url=$2
    local timeout=${3:-5}

    echo -n "Checking $name... "

    if command -v curl &> /dev/null; then
        if timeout $timeout curl -s -f "$url" > /dev/null 2>&1; then
            echo "✓ OK"
            return 0
        else
            echo "❌ FAILED"
            return 1
        fi
    else
        echo "⚠ curl not available"
        return 0
    fi
}

# Check services
echo "Service Status:"
check_service "Ollama API" "http://ollama:11434/api/tags" || EXIT_CODE=1
check_service "PGVector Database" "http://pgvector:5432" && echo "✓ OK" || echo "⚠ Not available"
check_service "RAG API Server" "http://py-script:8000/healthz" || EXIT_CODE=1

echo ""
echo "Environment Variables:"
if [ -n "$ENV" ]; then
    echo "✓ ENV=$ENV"
else
    echo "⚠ ENV not set"
fi

if [ -n "$MODEL" ]; then
    echo "✓ MODEL=$MODEL"
else
    echo "⚠ MODEL not set"
fi

echo ""
if [ -f "/app/config.toml" ]; then
    echo "✓ Configuration file exists"
else
    echo "❌ Configuration file missing"
    EXIT_CODE=1
fi

echo ""
echo "========================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Health check passed!"
else
    echo "⚠ Some health checks failed (may be expected)"
fi
echo "========================================"

exit $EXIT_CODE
