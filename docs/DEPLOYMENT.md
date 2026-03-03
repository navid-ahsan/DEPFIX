# Deployment Guide

This document provides instructions for deploying the RAG Framework in different environments.

## Prerequisites

- Python 3.9+
- PostgreSQL 12+ with pgvector extension
- Ollama (for local LLM inference)
- Docker & Docker Compose (optional, for containerized deployment)
- 4GB+ available VRAM for LLM inference
- Git

## Development Setup

### 1. Clone Repository

```bash
git clone <repo-url>
cd socialwork
```

### 2. Create Python Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development/testing
```

### 4. Configure Environment

Create a `.env` file in the project root:

```bash
cp .env.example .env
# Edit .env with your configuration
```

**Key environment variables:**

```ini
# LLM Configuration
LLM_TYPE=ollama
LLM_OLLAMA_HOST=http://localhost:11434
LLM_OLLAMA_MODEL=mistral:7b
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=2048

# Vector Database
VECTORDB_TYPE=pgvector
VECTORDB_POSTGRES_URL=postgresql+psycopg2://postgres:password@localhost:5432/vector_db
VECTORDB_COLLECTION_NAME=error_analysis
VECTORDB_CHUNK_SIZE=1024
VECTORDB_CHUNK_OVERLAP=300

# Environment
ENVIRONMENT=development
DEBUG=true
```

### 5. Start Services (Docker Compose)

```bash
# Start PostgreSQL and Ollama
docker-compose up -d

# Verify services are running
docker-compose ps
```

Services will be available at:
- PostgreSQL: `localhost:5432`
- Ollama: `http://localhost:11434`
- pgAdmin (optional): `http://localhost:5050`

### 6. Initialize Database

```bash
# The database is auto-initialized on first vector index operation
# Or manually:
python -m backend.app.models.database
```

### 7. Download LLM Model

If using Ollama:

```bash
# Pull a model (examples)
ollama pull mistral:7b
ollama pull llama2
ollama pull neural-chat

# List available models
ollama list

# Verify it's running
curl http://localhost:11434/api/tags
```

### 8. Start Backend Server

```bash
cd backend/app
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# The server will be available at http://localhost:8000
# API docs at http://localhost:8000/docs
# OpenAPI schema at http://localhost:8000/openapi.json
```

### 9. Test the System

```bash
# Query the RAG endpoint
curl -X POST http://localhost:8000/api/rag/query \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'query_text=How do I fix PyTorch import errors?' \
  -d 'dependencies=torch' \
  -d 'intent=guidance'

# Check health
curl http://localhost:8000/health
```

---

## Production Deployment

### Option 1: Standalone Server

For small to medium deployments on a single machine.

#### 1. System Requirements

- **OS**: Linux (Ubuntu 20.04+ recommended) or macOS
- **CPU**: 4+ cores
- **RAM**: 16GB+ (8GB minimum for LLM)
- **Storage**: 50GB+ (for models and data)
- **Network**: Stable internet for documentation scraping

#### 2. Installation

```bash
# Clone repo
git clone <repo-url> /opt/rag-framework
cd /opt/rag-framework

# Create service user
sudo useradd -m -s /bin/bash rag-user
sudo chown -R rag-user:rag-user /opt/rag-framework

# Setup venv
python3 -m venv /opt/rag-framework/.venv
source /opt/rag-framework/.venv/bin/activate
pip install -r requirements.txt
```

#### 3. Systemd Service Setup

Create `/etc/systemd/system/rag-framework.service`:

```ini
[Unit]
Description=RAG Framework Backend
After=network.target postgresql.service

[Service]
Type=notify
User=rag-user
WorkingDirectory=/opt/rag-framework
Environment="PATH=/opt/rag-framework/.venv/bin"
Environment="ENVIRONMENT=production"
ExecStart=/opt/rag-framework/.venv/bin/uvicorn \
          backend.app.main:app \
          --host 0.0.0.0 \
          --port 8000 \
          --workers 4 \
          --worker-class uvicorn.workers.UvicornWorker

Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable rag-framework
sudo systemctl start rag-framework
sudo systemctl status rag-framework
```

#### 4. Reverse Proxy Setup (Nginx)

Create `/etc/nginx/sites-available/rag-framework`:

```nginx
upstream rag_app {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 100M;

    location / {
        proxy_pass http://rag_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_request_buffering off;
    }

    # API documentation
    location /docs {
        proxy_pass http://rag_app;
    }

    location /openapi.json {
        proxy_pass http://rag_app;
    }
}
```

Enable and test:

```bash
sudo ln -s /etc/nginx/sites-available/rag-framework /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 5. SSL/TLS Setup

Using Let's Encrypt:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### Option 2: Docker Deployment

For standardized, reproducible deployments.

#### 1. Build Docker Image

```bash
# From project root
docker build -t rag-framework:latest .
```

#### 2. Run Container

```bash
docker run -d \
  --name rag-framework \
  -p 8000:8000 \
  -e VECTORDB_POSTGRES_URL=postgresql+psycopg2://user:pass@postgres:5432/vector_db \
  -e LLM_OLLAMA_HOST=http://ollama:11434 \
  -v rag-data:/app/data \
  --network rag-net \
  rag-framework:latest
```

#### 3. Docker Compose (Recommended)

See `docker-compose.yml` in project root for full multi-service setup:

```bash
docker-compose -f docker-compose.yml up -d
```

### Option 3: Kubernetes Deployment

For large-scale deployments with high availability.

#### 1. Prerequisites

```bash
kubectl cluster-info
helm version
```

#### 2. Install with Helm

```bash
# Add chart repository
helm repo add rag-framework https://charts.example.com
helm repo update

# Install
helm install rag-framework rag-framework/rag-framework \
  --namespace rag-system \
  --create-namespace \
  -f values-prod.yaml
```

#### 3. Verify Deployment

```bash
kubectl get pods -n rag-system
kubectl get svc -n rag-system
kubectl logs -n rag-system <pod-name>
```

See `deploy/values-production.yml` for detailed Helm configuration.

---

## Monitoring & Maintenance

### Health Checks

```bash
# Check API health
curl https://your-domain.com/health

# Check PostgreSQL
pg_isready -h localhost -U postgres

# Check Ollama
curl http://localhost:11434/api/tags
```

### Log Management

```bash
# Backend logs
tail -f /opt/rag-framework/logs/app.log

# Systemd logs
sudo journalctl -u rag-framework -f

# Docker logs
docker logs -f rag-framework
```

### Database Backups

```bash
# PostgreSQL backup
pg_dump -U postgres -h localhost vector_db > backup.sql

# Restore from backup
psql -U postgres -h localhost vector_db < backup.sql
```

### Performance Tuning

1. **Database**: Increase `work_mem` and `shared_buffers` in postgresql.conf
2. **LLM**: Use quantized models (Q4_K_M) for faster inference
3. **API**: Use multiple uvicorn workers (`--workers 4`)
4. **Vector DB**: Index optimization with pgvector

---

## Troubleshooting

### Connection Issues

```bash
# Test database connection
psql -U postgres -h localhost -d vector_db -c "SELECT 1"

# Test Ollama
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral:7b","prompt":"test"}'
```

### Memory Issues

- Reduce `chunk_size` in config
- Use smaller LLM model
- Increase system swap

### Slow Queries

- Add database indexes on `library` and `created_at` columns
- Use pgvector's IVFFlat index for large collections
- Profile with `EXPLAIN ANALYZE`

---

## Configuration Files

### Environment Variables

See `.env.example` for all available options.

### TOML Configuration

Edit `src/config.toml` for database and model settings.

### Pydantic Settings

`backend/app/config.py` contains the data model for all settings.

---

## Support & Rollback

### Rollback Procedure

```bash
# If new version has issues
git checkout <previous-tag>
pip install -r requirements.txt
systemctl restart rag-framework
```

### Emergency Contacts

- **Support**: support@example.com
- **On-Call**: on-call@example.com
- **Security**: security@example.com

---

**Last Updated**: March 2, 2026 | **Version**: 0.1.0
