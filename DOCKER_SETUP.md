# Docker Setup Guide for RAG Framework

## Overview

This guide explains how to run the entire RAG Framework stack using Docker containers with proper networking and configuration.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Network: rag-net               │
├────────────────┬──────────────────┬───────────┬──────────┤
│  Frontend      │  Backend API     │  Ollama   │ PostgreSQL│
│  :3000         │  :8000           │  :11434   │  :5432   │
│                │                  │           │          │
│  Next.js       │  FastAPI         │  LLM +    │  Vector  │
│  Application   │  (Python)        │  Embeddings│  DB     │
└────────────────┴──────────────────┴───────────┴──────────┘
         ↓                ↓              ↓           ↓
    Shared volumes   Source code    Model cache   Data volume
```

## Prerequisites

### 1. Install Docker Desktop

- **Windows/Mac**: Download from https://www.docker.com/products/docker-desktop
  - Install and enable WSL2 integration (Windows)
  - Allocate at least 4GB RAM and 2 CPU cores
  
- **Linux**: Install Docker Engine
  ```bash
  sudo apt-get update
  sudo apt-get install -y docker.io docker-compose
  sudo usermod -aG docker $USER
  ```

### 2. Verify Installation

```bash
docker --version
docker-compose --version
docker ps  # Test access
```

## Quick Start

### Step 1: Setup Environment

```bash
cd /home/navid/project/socialwork

# Load environment variables
export $(cat .env.docker | xargs)
```

### Step 2: Build and Start Containers

```bash
# Automated setup (recommended)
bash scripts/docker-setup.sh

# OR manual setup
docker-compose build
docker-compose up -d
```

### Step 3: Access Services

```
Frontend:    http://localhost:3000
Backend:     http://localhost:8000
Ollama:      http://localhost:11434
PostgreSQL:  localhost:5432
```

### Step 4: Verify Status

```bash
bash scripts/docker-utils.sh status
bash scripts/docker-utils.sh health
```

## Services Configuration

### Frontend Container

**Image**: rag-frontend:latest  
**Port**: 3000  
**Environment**:
- `NEXT_PUBLIC_API_URL=http://backend:8000`
- `NODE_ENV=production`

**Features**:
- Multi-stage Docker build for optimized size
- Health checks enabled
- Auto-restart on failure

### Backend Container

**Image**: rag-backend:latest  
**Port**: 8000  
**Environment**:
- `DATABASE_URL=postgresql://postgres:password123@pgvector:5432/vector_db`
- `OLLAMA_HOST=http://ollama:11434`

**Features**:
- Non-root user execution
- Health checks enabled
- Auto-initialization of database

### Ollama Container

**Image**: ollama/ollama:latest  
**Port**: 11434  
**Models**:
- `nomic-embed-text` (embeddings)
- `qwen3:8b` (LLM)

**Volume**: Shared across container restarts

### PostgreSQL Container

**Image**: ankane/pgvector:latest  
**Port**: 5432  
**Database**: vector_db  
**pgvector Extension**: Enabled for vector operations

## Networking

### Network Configuration

- **Name**: `rag-net`
- **Driver**: bridge
- **Subnet**: 172.20.0.0/16

### Service Discovery

Services communicate using container names:
- `frontend:3000` - Next.js frontend
- `backend:8000` - FastAPI backend
- `ollama:11434` - Ollama service
- `pgvector:5432` - PostgreSQL database

## Common Commands

### Start Services
```bash
docker-compose up -d
```

### View Logs
```bash
docker-compose logs -f                    # All services
docker-compose logs -f backend            # Specific service
docker logs -f rag-backend                # By container name
```

### Stop Services
```bash
docker-compose stop                       # Stop (not remove)
docker-compose down                       # Stop and remove containers
docker-compose down -v                    # Stop, remove, and delete volumes
```

### Restart Services
```bash
docker-compose restart                    # All containers
docker-compose restart backend            # Specific service
bash scripts/docker-utils.sh restart
```

### Connect to Services

```bash
# PostgreSQL shell
bash scripts/docker-utils.sh shell-db
# OR
docker exec -it pgvector psql -U postgres -d vector_db

# Backend shell
bash scripts/docker-utils.sh shell-backend
# OR
docker exec -it rag-backend bash

# Ollama shell
docker exec -it ollama bash
```

### Pull Models

```bash
bash scripts/docker-utils.sh pull-models
```

### Health Checks

```bash
bash scripts/docker-utils.sh health
```

## Environment Variables

### .env.docker

```env
# Database
DB_USER=postgres
DB_PASSWORD=password123
DB_NAME=vector_db
DB_PORT=5432

# Ollama
OLLAMA_HOST=http://ollama:11434
OLLAMA_PORT=11434

# Backend
API_PORT=8000
BACKEND_HOST=http://backend:8000
ENVIRONMENT=docker
DEBUG=false

# Frontend
FRONTEND_PORT=3000
NEXT_PUBLIC_API_URL=http://backend:8000

# Logging
LOG_LEVEL=INFO
PYTHONUNBUFFERED=1
```

### Overriding Variables

```bash
# Via environment
export DB_PASSWORD=mynewpassword
docker-compose up -d

# Via command line
docker-compose -f docker-compose.yml up -d pg=myvalue
```

## Volumes & Data Persistence

### PostgreSQL Data

**Volume**: `pgvector_data`  
**Location**: `/var/lib/postgresql/data`  
**Persistence**: All logs and dependencies data

### Ollama Models

**Volume**: `ollama_data`  
**Location**: `/root/.ollama`  
**Persistence**: Downloaded models cached

### Application Code

**Mount**: Shared from host  
**Location**: `/app` in container  
**Purpose**: Live code updates (development mode)

## Troubleshooting

### Services Not Starting

```bash
# Check logs
docker-compose logs

# Check Docker daemon
docker ps

# Restart Docker service
sudo systemctl restart docker
```

### Port Already in Use

```bash
# Find process using port
lsof -i :3000
netstat -tlnp | grep 3000

# OR change port in docker-compose.yml
```

### Ollama Models Not Found

```bash
# Pull models
docker exec ollama ollama pull nomic-embed-text
docker exec ollama ollama pull qwen3:8b

# Verify
curl http://localhost:11434/api/tags
```

### Database Connection Errors

```bash
# Check PostgreSQL is running
docker exec pgvector pg_isready -U postgres

# Check connection
docker exec pgvector psql -U postgres -d vector_db -c "SELECT 1"

# View database logs
docker-compose logs pgvector
```

### Slow Performance

1. **Increase Docker resources**:
   - Docker Desktop → Preferences → Resources
   - Increase Memory to 8GB+ and CPUs to 4+

2. **Check container status**:
   ```bash
   docker stats
   ```

3. **Check logs for errors**:
   ```bash
   docker-compose logs
   ```

## Production Deployment

### Database

Change `database_url` in `docker-compose.yml`:

```yaml
# For PostgreSQL (recommended)
DATABASE_URL: postgresql+psycopg2://pg_user:secure_pwd@pgvector:5432/vector_db

# For SQLite (local only)
DATABASE_URL: sqlite:///./rag_framework.db
```

### Security

1. **Change default passwords**:
   ```bash
   # Edit .env.docker
   DB_PASSWORD=your_strong_password_here
   ```

2. **Use environment file**:
   ```bash
   # Use secrets management
   docker-compose --env-file .env.production config
   ```

3. **Enable SSL/TLS**:
   - Use reverse proxy (nginx, Traefik)
   - Install SSL certificates
   - Configure in docker-compose.yml

## Monitoring

### Health Checks

All services include health checks:

```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

### Logs

```bash
# Real-time logs
docker-compose logs -f --tail=50

# Search logs
docker-compose logs | grep ERROR
```

### Performance Monitoring

```bash
# Container stats
docker stats

# Disk usage
docker system df
```

## Cleanup & Maintenance

### Remove Unused Data

```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune

# Remove unused volumes
docker volume prune

# Full cleanup (CAREFUL!)
docker system prune -a --volumes
```

### Backup PostgreSQL Data

```bash
# Backup database
docker exec pgvector pg_dump -U postgres vector_db > backup.sql

# Restore database
cat backup.sql | docker exec -i pgvector psql -U postgres -d vector_db
```

## Next Steps

1. **Test Phase 4**:
   ```bash
   bash scripts/docker-utils.sh health
   # Verify all services are healthy
   ```

2. **Upload Error Logs**:
   - Go to http://localhost:3000/dashboard
   - Upload test logs

3. **Run RAG Analysis**:
   - Select dependencies
   - Click "Analyze with AI"
   - Review suggestions

4. **Monitor Logs**:
   ```bash
   docker-compose logs -f backend
   ```

---

**For help with scripts**:
```bash
bash scripts/docker-setup.sh --help
bash scripts/docker-utils.sh help
```
