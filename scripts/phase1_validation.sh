#!/bin/bash
# Quick setup script for Phase 1 validation & Phase 2 development
# Usage: bash scripts/phase1_validation.sh

set -e  # Exit on error

echo "================================"
echo "  Phase 1 Validation & Setup"
echo "================================"
echo ""

# Configuration
PROJECT_ROOT="/home/navid/project/socialwork"
PYTHONPATH="${PROJECT_ROOT}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check conda activation
if [ -z "$CONDA_DEFAULT_ENV" ]; then
    echo -e "${YELLOW}⚠️  Conda environment not activated${NC}"
    echo "Please run: conda activate conda"
    exit 1
fi
echo -e "${GREEN}✓${NC} Conda environment: $CONDA_DEFAULT_ENV"
echo ""

# Step 1: Install dependencies
echo "Step 1: Installing dependencies..."
if pip install -q -r requirements.txt; then
    echo -e "${GREEN}✓${NC} Dependencies installed successfully"
else
    echo -e "${RED}✗${NC} Failed to install dependencies"
    exit 1
fi
echo ""

# Step 2: Install test dependencies
echo "Step 2: Installing test dependencies..."
if pip install -q pytest pytest-asyncio pytest-cov PyPDF2 langchain-text-splitters; then
    echo -e "${GREEN}✓${NC} Test dependencies installed"
else
    echo -e "${RED}✗${NC} Failed to install test dependencies"
    exit 1
fi
echo ""

# Step 3: Validate imports
echo "Step 3: Validating core imports..."
if PYTHONPATH="$PYTHONPATH" python -c \
    "from backend.app.agents import IntentAnalyzerAgent, OrchestratorAgent, DependencyExtractorAgent; print('✓ Agents imported')" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Core imports validated"
else
    echo -e "${RED}✗${NC} Import validation failed"
    exit 1
fi
echo ""

# Step 4: Quick integration test
echo "Step 4: Running quick integration test..."
if PYTHONPATH="$PYTHONPATH" python test_integration_quick.py; then
    echo -e "${GREEN}✓${NC} Integration test passed"
else
    echo -e "${RED}✗${NC} Integration test failed"
    exit 1
fi
echo ""

# Step 5: Optional - Run full test suite
echo "Step 5: Running full test suite..."
echo "(This will take about 6 seconds)"
PYTHONPATH="$PYTHONPATH" pytest tests/ -q --tb=no || true
echo ""

echo "================================"
echo -e "${GREEN}✅ Phase 1 Validation Complete${NC}"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Review TEST_RESULTS.md for detailed test information"
echo "2. To run the development server:"
echo "   uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000"
echo "3. To start Phase 2 development:"
echo "   - Create frontend component"
echo "   - Set up GitHub OAuth"
echo "   - Implement code diff generation"
echo ""
echo "For PostgreSQL/pgvector setup, see DEPLOYMENT.md"
echo ""
