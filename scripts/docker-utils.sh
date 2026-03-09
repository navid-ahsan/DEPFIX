#!/bin/bash
# Docker management utilities

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

show_help() {
    cat << EOF
RAG Framework Docker Management

Usage: bash scripts/docker-utils.sh [command]

Commands:
    start       Start all Docker containers
    stop        Stop all containers
    restart     Restart all containers
    logs        Show container logs (follow mode)
    status      Show container status
    clean       Remove containers and volumes (WARNING: Data loss)
    shell-db    Open PostgreSQL shell
    shell-backend  SSH into backend container
    pull-models    Download Ollama models
    health      Health check all services
    help        Show this help message

Examples:
    bash scripts/docker-utils.sh start
    bash scripts/docker-utils.sh logs
    bash scripts/docker-utils.sh status
EOF
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker is not installed${NC}"
        exit 1
    fi
}

start_containers() {
    echo -e "${BLUE}🚀 Starting containers...${NC}"
    cd "$PROJECT_ROOT"
    docker-compose up -d
    echo -e "${GREEN}✓ Containers started${NC}"
    sleep 3
    show_status
}

stop_containers() {
    echo -e "${BLUE}⏹️  Stopping containers...${NC}"
    cd "$PROJECT_ROOT"
    docker-compose down
    echo -e "${GREEN}✓ Containers stopped${NC}"
}

restart_containers() {
    echo -e "${BLUE}🔄 Restarting containers...${NC}"
    cd "$PROJECT_ROOT"
    docker-compose restart
    echo -e "${GREEN}✓ Containers restarted${NC}"
    sleep 3
    show_status
}

show_logs() {
    echo -e "${BLUE}📋 Following logs (Ctrl+C to exit)...${NC}"
    cd "$PROJECT_ROOT"
    docker-compose logs -f
}

show_status() {
    echo -e "${BLUE}📊 Container Status:${NC}"
    cd "$PROJECT_ROOT"
    docker-compose ps
    
    echo ""
    echo -e "${BLUE}🔗 Service URLs:${NC}"
    echo "  Frontend    → http://localhost:3000"
    echo "  Backend API → http://localhost:8000/health"
    echo "  Ollama      → http://localhost:11434/api/tags"
    echo "  PostgreSQL  → postgres://postgres:password123@localhost:5432/vector_db"
}

clean_all() {
    echo -e "${YELLOW}⚠️  WARNING: This will delete all containers and volumes!${NC}"
    read -p "Are you sure? (yes/no) " -n 3 -r
    echo
    if [[ $REPLY == "yes" ]]; then
        echo -e "${BLUE}🗑️  Cleaning up...${NC}"
        cd "$PROJECT_ROOT"
        docker-compose down -v
        echo -e "${GREEN}✓ Cleanup complete${NC}"
    else
        echo "Cancelled"
    fi
}

shell_db() {
    echo -e "${BLUE}🐘 Connecting to PostgreSQL...${NC}"
    docker exec -it pgvector psql -U postgres -d vector_db
}

shell_backend() {
    echo -e "${BLUE}🔧 Connecting to backend...${NC}"
    docker exec -it rag-backend bash
}

pull_models() {
    echo -e "${BLUE}🤖 Pulling Ollama models...${NC}"
    
    echo "Pulling nomic-embed-text..."
    docker exec ollama ollama pull nomic-embed-text
    
    echo ""
    echo "Pulling qwen3:8b..."
    docker exec ollama ollama pull qwen3:8b
    
    echo -e "${GREEN}✓ Models pulled${NC}"
}

health_check() {
    echo -e "${BLUE}🏥 Health Check:${NC}"
    
    echo ""
    echo "Frontend: " && curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000 && echo "  ✓ OK" || echo "  ❌ DOWN"
    
    echo ""
    echo "Backend: " && curl -s http://localhost:8000/health | python3 -m json.tool && echo "  ✓ OK" || echo "  ❌ DOWN"
    
    echo ""
    echo "Ollama: " && curl -s http://localhost:11434/api/tags | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(f'  Models: {len(data[\"models\"])} available')
    for m in data['models']:
        print(f'    • {m[\"name\"]}')
except:
    print('  ❌ Error')
" || echo "  ❌ DOWN"
    
    echo ""
    echo "PostgreSQL: " && docker exec pgvector pg_isready -U postgres > /dev/null 2>&1 && echo "  ✓ OK" || echo "  ❌ DOWN"
}

# Main
check_docker

case "${1:-help}" in
    start)
        start_containers
        ;;
    stop)
        stop_containers
        ;;
    restart)
        restart_containers
        ;;
    logs)
        show_logs
        ;;
    status)
        show_status
        ;;
    clean)
        clean_all
        ;;
    shell-db)
        shell_db
        ;;
    shell-backend)
        shell_backend
        ;;
    pull-models)
        pull_models
        ;;
    health)
        health_check
        ;;
    help|*)
        show_help
        ;;
esac
