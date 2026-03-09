# Docker Setup Summary

**Date**: March 5, 2026  
**Status**: ✅ Ready for Phase 4 Testing

## What's Been Set Up

### Docker Containers

1. **rag-frontend** (Next.js)
   - Port: 3000
   - Status: Ready
   - Dockerfile: frontend/Dockerfile (created)

2. **rag-backend** (FastAPI)
   - Port: 8000
   - Status: Ready
   - Database: PostgreSQL with pgvector
   - Dockerfile: Dockerfile (updated)

3. **ollama** (LLM + Embeddings)
   - Port: 11434
   - Models: nomic-embed-text, qwen3:8b
   - Volume: ollama_data

4. **pgvector** (PostgreSQL Database)
   - Port: 5432
   - Database: vector_db
   - User: postgres
   - Volume: pgvector_data

### Network Configuration

- **Network**: rag-net
- **Type**: Bridge network
- **Subnet**: 172.20.0.0/16
- **Service Discovery**: Using container names (e.g., backend:8000)

### Environment Configuration

- **File**: .env.docker
- **Database Credentials**:
  - User: postgres
  - Password: password123
  - Database: vector_db
- **API Endpoints**:
  - Backend: http://backend:8000
  - Frontend: http://localhost:3000

## Files Created

### Configuration
- ✅ `.env.docker` - Environment variables for Docker
- ✅ `docker-compose.yml` - Updated with all services
- ✅ `frontend/Dockerfile` - Next.js container
- ✅ `Dockerfile` - Backend FastAPI container
- ✅ `frontend/.dockerignore` - Build ignore patterns

### Helper Scripts
- ✅ `scripts/docker-setup.sh` - Automated setup script
- ✅ `scripts/docker-utils.sh` - Container management utilities

### Documentation
- ✅ `DOCKER_SETUP.md` - Comprehensive Docker guide
- ✅ `SETUP_GUIDE.md` - Overall setup guide (existing, updated)

## Quick Start Commands

### First Time Setup
```bash
cd /home/navid/project/socialwork
bash scripts/docker-setup.sh
```

This will:
1. ✅ Check Docker installation
2. ✅ Build all images
3. ✅ Start all containers
4. ✅ Pull Ollama models
5. ✅ Show service URLs

### Daily Operations

```bash
# Start containers
bash scripts/docker-utils.sh start

# Check status
bash scripts/docker-utils.sh status

# View logs
bash scripts/docker-utils.sh logs

# Health check
bash scripts/docker-utils.sh health

# Stop containers
bash scripts/docker-utils.sh stop
```

## Service Communication

### Frontend → Backend
```
http://localhost:3000 → http://backend:8000
(Browser)             (Container network)
```

### Backend → Database
```
backend:8000 → postgresql+psycopg2://postgres:password123@pgvector:5432/vector_db
```

### Backend → Ollama
```
backend:8000 → http://ollama:11434/api/generate
```

## Deployment Options

### Local SQLite (Current)
- No Docker needed for testing
- Works with local Ollama
- Default configuration

### Docker with PostgreSQL (Production)
```bash
# Start Docker containers
bash scripts/docker-setup.sh

# Services automatically configured for Docker
# Database URL set to PostgreSQL
# All services networked together
```

## Next Steps

### Option 1: Test Locally (No Docker)
```bash
# Backend already running on localhost:8000
# Frontend already running on localhost:3000
# Ollama already running on localhost:11434
go-to http://localhost:3000/dashboard
```

### Option 2: Test with Docker
```bash
# Prerequisites: Docker Desktop installed
bash scripts/docker-setup.sh

# Then test
curl http://localhost:8000/health
curl http://localhost:3000
```

## Troubleshooting

### Docker Not Installed?
- Download Docker Desktop: https://www.docker.com/products/docker-desktop
- Enable WSL2 integration (Windows)

### Need to Change Ports?
Edit `docker-compose.yml`:
```yaml
backend:
  ports:
    - "8001:8000"  # Change left number
```

### Database Password Too Weak?
Edit `.env.docker`:
```env
DB_PASSWORD=your_strong_password_here
```

### Container Crashes?
```bash
bash scripts/docker-utils.sh logs
# Check error messages
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                 Docker Network (rag-net)                │
├──────────────┬────────────────┬──────────┬──────────────┤
│  Frontend    │  Backend       │  Ollama  │  PostgreSQL  │
│  :3000       │  :8000         │  :11434  │  :5432       │
│              │                │          │              │
│  Next.js     │  FastAPI       │  Models  │  Vector DB   │
├──────────────┼────────────────┼──────────┼──────────────┤
│ Node.js env  │ Python env     │ Linux    │ Ubuntu       │
│ Health check │ Health check   │ H.check  │ Health check │
└──────────────┴────────────────┴──────────┴──────────────┘
       ↓              ↓                ↓           ↓
   Volumes        Source code     Models      Data
```

## Performance Notes

- **Memory**: 8GB recommended, 4GB minimum
- **CPU**: 4 cores recommended, 2 cores minimum
- **Storage**: 20GB for models and data
- **Network**: All services communicate internally (no internet overhead)

## Security Considerations

⚠️ **Development Setup** - Not for production
- Default passwords used
- No SSL/TLS configured
- Debug mode could be enabled

✅ **For Production**:
1. Change all default passwords
2. Enable SSL/TLS
3. Use Docker secrets for credentials
4. Run health checks
5. Configure monitoring

---

**Status**: ✅ All Docker containers ready for Phase 4 testing!

For detailed commands, run:
```bash
bash scripts/docker-utils.sh help
```
