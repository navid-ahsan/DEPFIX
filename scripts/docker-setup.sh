#!/bin/bash
# Docker initialization script
# This script sets up the Docker containers and pulls necessary models

set -e

echo "=========================================="
echo "RAG Framework Docker Setup"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    echo "Please install Docker Desktop from https://www.docker.com/products/docker-desktop"
    exit 1
fi

echo -e "${BLUE}📦 Docker version:${NC}"
docker --version
echo ""

# Check docker-compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    exit 1
fi

echo -e "${BLUE}📦 Docker Compose version:${NC}"
docker-compose version || docker compose version
echo ""

# Load environment file
if [ -f ".env.docker" ]; then
    echo -e "${GREEN}✓ Loading .env.docker${NC}"
    export $(grep -v '^#' .env.docker | grep -v '^$' | xargs)
else
    echo -e "${RED}⚠ Warning: .env.docker not found, using defaults${NC}"
fi

# Build images
echo ""
echo -e "${BLUE}🔨 Building Docker images...${NC}"
docker-compose build --no-cache

# Start services
echo ""
echo -e "${BLUE}🚀 Starting services...${NC}"
docker-compose up -d

# Wait for services to be ready
echo ""
echo -e "${BLUE}⏳ Waiting for services to be healthy...${NC}"
sleep 10

# Check Ollama
echo ""
echo -e "${BLUE}🤖 Setting up Ollama models...${NC}"

# Wait for Ollama to be ready
echo "Waiting for Ollama to be responsive..."
MAX_ATTEMPTS=30
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Ollama is responsive${NC}"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    echo "Attempt $ATTEMPT/$MAX_ATTEMPTS..."
    sleep 2
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo -e "${RED}❌ Ollama failed to start${NC}"
else
    # Pull models
    echo ""
    echo "Pulling nomic-embed-text model (embeddings)..."
    docker exec ollama ollama pull nomic-embed-text
    
    echo "Pulling qwen3:8b model (LLM)..."
    docker exec ollama ollama pull qwen3:8b
    
    echo -e "${GREEN}✓ Models pulled successfully${NC}"
fi

# Check database
echo ""
echo -e "${BLUE}🗄️ Setting up database...${NC}"
if docker exec pgvector pg_isready -U postgres > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
else
    echo -e "${RED}⚠ PostgreSQL may still be starting${NC}"
fi

# Display status
echo ""
echo "=========================================="
echo -e "${GREEN}✅ Docker setup complete!${NC}"
echo "=========================================="
echo ""
echo "Services running:"
echo -e "  ${BLUE}Frontend${NC}    → http://localhost:3000"
echo -e "  ${BLUE}Backend API${NC}   → http://localhost:8000"
echo -e "  ${BLUE}Ollama${NC}       → http://localhost:11434"
echo -e "  ${BLUE}PostgreSQL${NC}   → localhost:5432"
echo ""
echo "Useful commands:"
echo "  docker-compose ps              # Show running containers"
echo "  docker-compose logs -f         # View logs"
echo "  docker-compose down            # Stop all services"
echo "  docker-compose down -v         # Stop services and remove volumes"
echo ""
