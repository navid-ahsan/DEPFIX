# RAG Application Deployment Guide

This directory contains deployment configurations for different environments.

## Directory Structure

```
deploy/
├── docker-compose-staging.yml      # Docker Compose override for staging
├── values-staging.yml              # Kubernetes/Helm values for staging
├── values-production.yml           # Kubernetes/Helm values for production
└── README.md                       # This file
```

## Environments

### Staging Environment
- **Model**: mistral:7b (smaller, faster for testing)
- **Database**: Separate staging PostgreSQL with PGVector
- **GPU**: Optional (not required)
- **Purpose**: Development, testing, and validation

**Deploy with Docker Compose:**
```bash
docker-compose -f docker-compose.yml -f deploy/docker-compose-staging.yml up -d
```

**Configuration**: Edit `deploy/values-staging.yml` before deployment

### Production Environment
- **Model**: my_llama4:latest (larger, more accurate)
- **Database**: Production PostgreSQL with PGVector and backups
- **GPU**: NVIDIA GPU required
- **Purpose**: Live inference and production workloads

**Deploy via GitLab CI/CD:**
- Manually approve the `deploy:production` job in GitLab
- Pipeline will automatically deploy using production configuration

**Configuration**: Edit `deploy/values-production.yml` before deployment

## Future: Kubernetes Deployment

The `values-*.yml` files are prepared for Kubernetes/Helm deployment. To implement:

1. Create Helm chart templates in `deploy/chart/`
2. Use values files to configure environment-specific settings
3. Deploy with:
   ```bash
   helm install rag-app ./deploy/chart -f deploy/values-production.yml
   ```

## Usage Examples

### Local Development (Staging)
```bash
cd /path/to/project
docker-compose -f docker-compose.yml -f deploy/docker-compose-staging.yml up -d
```

### Testing Deployment
```bash
# Check service health
bash scripts/health_check.sh

# Run evaluation
bash scripts/run_evaluation.sh lab_model mistral:7b
```

### Production Deployment
1. Commit changes to `main` branch
2. Wait for CI/CD pipeline to complete tests and build
3. Go to GitLab project > CI/CD > Pipelines
4. Click "Play" button on `deploy:production` job
5. Monitor deployment progress

### Rollback Production
If something goes wrong in production:
1. Go to CI/CD > Pipelines
2. Find a previous successful deployment
3. Click "Play" on the `rollback:production` job from that pipeline

## Environment Variables

Copy `.env.example` to `.env` and customize:
```bash
cp .env.example .env
# Edit .env with your environment-specific values
```

Key variables:
- `ENV`: lab_model or dgx_model
- `MODEL`: Model identifier (mistral:7b, my_llama4:latest, etc.)
- `DATABASE_URL`: PostgreSQL connection string
- `OLLAMA_HOST`: Ollama API endpoint
- `CUDA_VISIBLE_DEVICES`: GPU devices to use (production only)

## Monitoring & Health Checks

All services include health checks:

```bash
# Manual health check
bash scripts/health_check.sh

# Docker health status
docker ps --format "table {{.Names}}\t{{.Status}}"

# Check specific service logs
docker logs py-script
docker logs ollama
docker logs pgvector
```

## Database Backups

For production:
- PostgreSQL PGVector database is backed up daily
- Backup configuration in `values-production.yml`
- Restore point: Last 30 days

## Security Considerations

1. **Networking**: Services only communicate on internal `rag-net` network
2. **Non-root User**: Application runs as non-root `appuser`
3. **Secrets**: Database passwords in `.env` (never commit this file)
4. **API Authentication**: Consider adding auth layer to production API
5. **HTTPS**: Production uses TLS/HTTPS (configure in Ingress)

## Troubleshooting

### Services not starting
```bash
docker-compose logs pgvector
docker-compose logs ollama
docker-compose logs py-script
```

### Health check failing
```bash
# Verify connectivity
curl -f http://ollama:11434/api/tags
curl -f http://py-script:8000/healthz
```

### Database connection issues
```bash
# Check PostgreSQL
docker exec pgvector psql -U postgres -d vector_db -c "SELECT 1;"
```

## Support

For issues or questions:
1. Check application logs: `docker logs <service>`
2. Run health checks: `bash scripts/health_check.sh`
3. Validate dependencies: `bash scripts/validate_dependencies.sh`
