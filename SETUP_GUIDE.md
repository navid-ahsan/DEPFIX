# Phase 4 RAG Framework - Complete Setup Guide

## Current Status (March 5, 2026)

### ✅ What's Already Working

**Local Setup:**
- ✅ Ollama running on `http://localhost:11434`
  - ✅ Model: `nomic-embed-text` (137M) - Embedding/retrieval
  - ✅ Model: `qwen3:8b` (8.2B) - LLM for code generation
- ✅ SQLite database: `./rag_framework.db` (local, no Docker needed)
- ✅ Backend FastAPI: `http://localhost:8000`
- ✅ Frontend Next.js: `http://localhost:3000`

**Phase 4 Features Ready:**
- Log upload and processing
- Dependency selection with embedding
- RAG-powered error analysis
- AI-suggested fixes with approval/rejection
- Evaluation tracking

---

## Prerequisites

### 1. Ollama (Already Installed ✅)

```bash
# Verify Ollama is running
curl -s http://localhost:11434/api/tags | python3 -m json.tool

# You should see:
# - nomic-embed-text (embedding model)
# - qwen3:8b (LLM model)
```

### 2. Python Environment

```bash
# Activate environment
cd /home/navid/project/socialwork
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Database (SQLite - Already Configured ✅)

Database is configured in `backend/app/config.py`:
```python
database_url = "sqlite:///./rag_framework.db"
```

Tables are auto-created on startup. No additional setup needed!

---

## Running Phase 4

### 1. Start Backend

```bash
# Terminal 1
cd /home/navid/project/socialwork
source .venv/bin/activate
python -m uvicorn backend.app.main:app --port 8000
```

Verify backend: `curl http://localhost:8000/health`

### 2. Start Frontend (if not running)

```bash
# Terminal 2
cd /home/navid/project/socialwork/frontend
npm run dev
```

Frontend URL: `http://localhost:3000`

### 3. Test Phase 4 End-to-End

**Step 1: Upload Error Log**
1. Go to `http://localhost:3000/dashboard`
2. Click "Upload Error Log"
3. Select any `.log` or `.txt` file (e.g., sample error log)
4. Upload and wait for processing

**Step 2: Select Dependencies**
1. Dashboard shows uploaded log with error count
2. Click "Select Dependencies"
3. Choose relevant packages (torch, monai, etc.)
4. Click "Start Embedding"
5. Wait ~5-10 seconds for embedding to complete

**Step 3: AI Analysis**
1. Error summary displays
2. Click "Analyze with AI"
3. System retrieves relevant documentation
4. AI generates fix suggestions:
   - Root Cause
   - Solution
   - Code Fix
   - Prevention Tips

**Step 4: Feedback & Evaluation**
1. Review AI-suggested fix
2. Click "This Helps!" to approve
3. Optional: Add feedback
4. Fix is recorded for learning

---

## Configuration

### Ollama Settings

File: `backend/app/config.py`

```python
class LLMSettings(BaseSettings):
    type: str = "ollama"
    ollama_host: str = "http://localhost:11434"  # Local address
    ollama_model: str = "qwen3:8b"  # Your LLM model
    temperature: float = 0.2
    timeout: int = 120

class EmbeddingSettings(BaseSettings):
    type: str = "ollama"
    ollama_host: str = "http://localhost:11434"
    model: str = "nomic-embed-text"  # Embedding model
```

### Database Settings

```python
# For local SQLite (default)
database_url = "sqlite:///./rag_framework.db"

# For PostgreSQL with pgvector (future)
# database_url = "postgresql+psycopg2://user:password@localhost/vector_db"
```

---

## Docker Setup (For Production/Scaling)

If you want to use Docker with pgvector instead of SQLite:

### Prerequisites
1. **Install Docker Desktop** on Windows/Mac
   - https://www.docker.com/products/docker-desktop
   - Enable WSL2 integration in settings

2. **Verify Docker**
   ```bash
   docker --version
   docker-compose --version
   ```

### Run Full Stack in Docker

```bash
cd /home/navid/project/socialwork

# Start all services
docker-compose up -d

# Services created:
# - pgvector:5432 (PostgreSQL + vector extension)
# - ollama:11434 (LLM + embeddings)
# - backend:8000 (FastAPI)

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Clean up (remove volumes)
docker-compose down -v
```

### Pull Models in Docker

```bash
# Access Ollama container
docker exec -it ollama ollama pull nomic-embed-text
docker exec -it ollama ollama pull qwen3:8b
```

---

## Troubleshooting

### Issue: "Ollama embeddings not available"
**Solution:** Models not pulled. Run:
```bash
ollama pull nomic-embed-text
ollama pull qwen3:8b
```

### Issue: "Log not found" in RAG analysis
**Solution:** Make sure you:
1. Upload a log file first
2. Wait for "Log processed" status
3. Then click "Analyze with AI"

### Issue: AI fix generation is slow
**Solution:** Normal for first run (5-30s). Check:
```bash
# Verify Ollama is responsive
curl -s http://localhost:11434/api/tags
```

### Issue: Long embedding time
**Solution:** Expected when Ollama not running. Falls back to mock with warnings.

---

## API Endpoints (Phase 4)

### Log Management
- `POST /api/v1/logs` - Upload error log
- `GET /api/v1/logs` - List all logs
- `GET /api/v1/logs/{log_id}` - Get log details

### RAG Analysis
- `POST /api/v1/rag/analyze-error-log` - Analyze with AI
- `GET /api/v1/rag/query/{query_id}` - Get analysis result
- `POST /api/v1/rag/approve-fix/{query_id}` - Approve fix
- `POST /api/v1/rag/reject-fix/{query_id}` - Reject fix

### Embedding
- `POST /api/v1/embedding/start` - Start embedding
- `GET /api/v1/embedding/status` - Check embedding status

---

## Next Steps

### Immediate (This Session)
- [ ] Test Phase 4 end-to-end with sample logs
- [ ] Verify RAG analysis works
- [ ] Toggle AI approval/rejection

### Short-term (Next Session)
- [ ] Setup Docker with PostgreSQL for production
- [ ] Configure GitHub integration
- [ ] Implement PR auto-generation (optional)

### Long-term (Future)
- [ ] Vector embeddings in pgvector (replace mock)
- [ ] Multiple LLM support (GPT, Claude, etc.)
- [ ] Automated CI/CD integration
- [ ] Evaluation metrics dashboard

---

## Quick Reference

```bash
# Check Ollama
curl -s http://localhost:11434/api/tags | python3 -m json.tool

# Check Backend
curl -s http://localhost:8000/health | python3 -m json.tool

# Check Database
sqlite3 rag_framework.db "SELECT COUNT(*) FROM logs;"

# Check Frontend
curl -s http://localhost:3000/dashboard
```

---

**Last Updated:** March 5, 2026  
**Status:** Phase 4 Ready for Testing ✅
