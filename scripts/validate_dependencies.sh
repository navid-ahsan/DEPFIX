#!/bin/bash
# Validation script to check dependencies are correctly installed
# Usage: bash scripts/validate_dependencies.sh

set -e

echo "========================================"
echo "RAG Application Dependency Validator"
echo "========================================"
echo ""

EXIT_CODE=0

# Check Python version
echo "Checking Python version..."
if ! python3 --version > /dev/null 2>&1; then
    echo "❌ Python 3 is not installed"
    EXIT_CODE=1
else
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo "✓ Python $PYTHON_VERSION found"
fi

# Check pip
echo "Checking pip..."
if ! pip --version > /dev/null 2>&1; then
    echo "❌ pip is not installed"
    EXIT_CODE=1
else
    PIP_VERSION=$(pip --version | awk '{print $2}')
    echo "✓ pip $PIP_VERSION found"
fi

echo ""
echo "Checking required Python packages..."

# Array of required packages
REQUIRED_PACKAGES=(
    "toml"
    "ollama"
    "aiofiles"
    "langchain"
    "langchain_community"
    "langchain_ollama"
    "langchain_postgres"
    "psycopg2"
    "pgvector"
    "pydantic"
    "fastapi"
    "uvicorn"
    "ragas"
    "datasets"
)

for package in "${REQUIRED_PACKAGES[@]}"; do
    if python3 -c "import ${package}" 2>/dev/null; then
        PACKAGE_VERSION=$(python3 -c "import ${package}; print(getattr(${package}, '__version__', 'unknown'))" 2>/dev/null || echo "unknown")
        echo "✓ $package ($PACKAGE_VERSION)"
    else
        echo "❌ $package is missing"
        EXIT_CODE=1
    fi
done

echo ""
echo "Checking service connectivity..."

# Try to ping Ollama
if command -v curl &> /dev/null; then
    if curl -s http://ollama:11434/api/tags > /dev/null 2>&1; then
        echo "✓ Ollama service is reachable"
    else
        echo "⚠ Ollama service is not reachable (may be expected in CI)"
    fi

    # Try to ping PGVector
    if curl -s http://pgvector:5432 > /dev/null 2>&1; then
        echo "✓ PGVector service is reachable"
    else
        echo "⚠ PGVector service is not reachable (may be expected in CI)"
    fi
else
    echo "⚠ curl is not installed - skipping service checks"
fi

echo ""
echo "========================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ All checks passed!"
else
    echo "❌ Some checks failed!"
fi
echo "========================================"

exit $EXIT_CODE
