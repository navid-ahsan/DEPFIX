# Phase 2: Frontend-Backend Integration Guide

**Last Updated:** March 3, 2026

## Overview

This guide explains how the Phase 2 frontend integrates with the Phase 1 backend RAG system.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                      │
│                   (localhost:3000)                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Pages:                                              │  │
│  │  - Home Page (Login)                                 │  │
│  │  - Dashboard (Analysis + Results)                    │  │
│  │  - PR Creation Flow                                  │  │
│  │                                                      │  │
│  │  Components:                                         │  │
│  │  - Auth (NextAuth + GitHub OAuth)                   │  │
│  │  - Log Input Form                                    │  │
│  │  - Results Display                                   │  │
│  │  - PR Preview                                        │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────┬──────────────────────────────────────────┘
                   │ HTTP/JSON (Axios)
                   │ Authorization: Bearer Token
                   │
┌──────────────────▼──────────────────────────────────────────┐
│                    Backend (FastAPI)                        │
│                   (localhost:8000)                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  /api/analyze (POST)         → Analysis Engine      │  │
│  │  /api/analyses (GET)        → Results Storage       │  │
│  │  /api/pull-requests (POST)  → GitHub Integration    │  │
│  │                                                      │  │
│  │  Internal Components:                                │  │
│  │  - RAG Engine (11 Agents)                           │  │
│  │  - Vector Database (PGVector)                        │  │
│  │  - LLM Integration (Ollama)                         │  │
│  │  - Log Processing Pipeline                          │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## API Endpoints

### 1. Analysis Endpoints

#### Submit Logs for Analysis
```http
POST /api/analyze
Content-Type: application/json
Authorization: Bearer <token>

{
  "logs": "ERROR: Docker build failed...",
  "repository": "owner/repo",
  "branch": "main"
}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "error": "Docker build failed: command not found: gcc",
  "error_type": "BuildError",
  "solution": "Install build-essential package",
  "confidence": 0.95,
  "code_snippet": "RUN apt-get install -y build-essential",
  "timestamp": "2026-03-03T13:42:00.000Z",
  "metadata": {
    "duration": 2.35,
    "model_used": "llama2",
    "source_documents": ["dockerfile-best-practices"]
  }
}
```

#### Get Analysis History
```http
GET /api/analyses
Authorization: Bearer <token>
```

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "completed",
    "error": "Docker build failed...",
    ...
  },
  ...
]
```

#### Get Single Analysis
```http
GET /api/analyses/{analysis_id}
Authorization: Bearer <token>
```

### 2. Pull Request Endpoints

#### Create Pull Request
```http
POST /api/pull-requests
Content-Type: application/json
Authorization: Bearer <token>

{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Fix: Install missing build dependencies",
  "body": "# Fix Docker Build Error\n\nInstalls required build tools.",
  "branch": "main"
}
```

**Response:**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "title": "Fix: Install missing build dependencies",
  "body": "# Fix Docker Build Error\n\nInstalls required build tools.",
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "draft",
  "url": null
}
```

#### Submit Pull Request to GitHub
```http
PUT /api/pull-requests/{pr_id}/submit
Authorization: Bearer <token>
```

#### Get Pull Requests
```http
GET /api/pull-requests
Authorization: Bearer <token>
```

## Setup Instructions

### Step 1: Start the Backend

```bash
cd /home/navid/project/socialwork
source .venv/bin/activate
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### Step 2: Install Frontend Dependencies

```bash
cd frontend
npm install
```

This installs:
- Next.js 14
- React 18
- NextAuth.js 4.24
- Axios 1.6
- Tailwind CSS 3.3

### Step 3: Configure Frontend Environment

```bash
cd frontend
cp .env.example .env.local
```

Edit `.env.local`:
```env
GITHUB_ID=<your-github-id>
GITHUB_SECRET=<your-github-secret>
NEXTAUTH_SECRET=<generated-secret>
NEXTAUTH_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Step 4: Start Frontend Development Server

```bash
cd frontend
npm run dev
```

Expected output:
```
> next dev
  ▲ Next.js 14.0.0
  - Local:        http://localhost:3000
```

## Data Flow

### 1. User Authentication
```
User clicks "Sign in with GitHub"
    ↓
Frontend redirects to /auth/github
    ↓
NextAuth initiates GitHub OAuth flow
    ↓
GitHub grants authorization
    ↓
NextAuth stores session with access token
    ↓
User redirected to /dashboard
```

### 2. Analysis Submission
```
User enters CI/CD logs in dashboard
    ↓
Frontend sends POST /api/analyze with logs
    ↓
Backend RAG engine processes logs
    ↓
Agents extract errors and generate solutions
    ↓
Backend returns AnalysisResult
    ↓
Frontend displays results with confidence score
    ↓
User can create PR with suggested fix
```

### 3. Pull Request Creation
```
User clicks "Create Pull Request"
    ↓
Frontend displays PR composition form
    ↓
User configures title, description, branch
    ↓
Frontend sends POST /api/pull-requests
    ↓
Backend creates PR draft
    ↓
User reviews and clicks "Submit"
    ↓
Frontend sends PUT /api/pull-requests/{id}/submit
    ↓
Backend creates actual PR on GitHub
    ↓
Frontend displays PR link to user
```

## File Structure

```
/home/navid/project/socialwork/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── analysis.py          ← NEW: Frontend API endpoints
│   │   │   ├── logs.py
│   │   │   ├── rag.py
│   │   │   └── ...
│   │   ├── agents/                  ← RAG Agents (Phase 1)
│   │   ├── core/                    ← RAG Engine (Phase 1)
│   │   └── main.py                  ← Updated: Includes analysis router
│   └── ...
├── frontend/                         ← NEW: Phase 2 Frontend
│   ├── app/
│   │   ├── api/
│   │   │   └── auth/[...nextauth]/route.ts
│   │   ├── auth/
│   │   │   └── github/page.tsx
│   │   ├── dashboard/
│   │   │   └── page.tsx
│   │   └── page.tsx
│   ├── lib/
│   │   └── api.ts                   ← API client utilities
│   ├── types/
│   │   └── index.ts                 ← TypeScript interfaces
│   ├── package.json
│   ├── next.config.js
│   └── README.md
└── docs/
    ├── PHASE2_FRONTEND.md
    ├── PHASE2_INTEGRATION.md         ← This file
    └── ...
```

## Testing the Integration

### 1. Test Backend Health
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "RAG CI/CD Framework",
  "version": "0.1.0"
}
```

### 2. Test Analysis Endpoint
```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "logs": "ERROR: Command not found"
  }'
```

Response should include analysis ID and solution.

### 3. Test Frontend Login Flow
1. Open http://localhost:3000
2. Click "Sign in with GitHub"
3. Authorize the application
4. Should redirect to /dashboard

### 4. Test Analysis Submission
1. On dashboard, paste CI/CD logs
2. Click "Analyze"
3. Frontend should display results with confidence score

## Authentication

### Frontend (NextAuth)
- Handles GitHub OAuth flow
- Manages user sessions
- Stores access token securely
- Sends token with each API request via `Authorization: Bearer <token>` header

### Backend
- Currently validates token presence (Authorization header required)
- TODO: Validate token signature and expiry
- TODO: Map token to user for multi-user support

## CORS Configuration

Backend is configured with CORS middleware:
```python
allow_origins=["http://localhost:3000", ...]
allow_credentials=True
allow_methods=["*"]
allow_headers=["*"]
```

Update in `backend/app/config.py` for production:
```python
CORS_ORIGINS = [
    "https://yourdomain.com",
    "https://www.yourdomain.com"
]
```

## Error Handling

### Common Errors

#### 1. "Cannot connect to backend"
**Frontend Error:** `Network Error` when submitting analysis

**Solution:**
```bash
# Verify backend is running
curl http://localhost:8000/health

# Check CORS headers
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: POST" \
     http://localhost:8000/api/analyze
```

#### 2. "Session expired"
**Frontend Error:** Redirected to login page

**Solution:**
- Check `NEXTAUTH_URL` matches domain
- Verify `NEXTAUTH_SECRET` is set
- Clear browser cookies and try again

#### 3. "Authorization failed"
**Backend Error:** 401 Unauthorized

**Solution:**
- Verify Authorization header is sent
- Check token format: `Bearer <token>`
- Regenerate GitHub OAuth credentials

#### 4. "CORS error"
**Frontend Error:** `Cross-Origin Request Blocked`

**Solution:**
- Verify backend CORS includes frontend origin
- Check `NEXT_PUBLIC_API_URL` environment variable
- Restart backend after CORS changes

## Performance Considerations

### Frontend Optimization
- Tailwind CSS builds minimal only used styles (~50KB gzipped)
- Next.js automatic code splitting
- Image optimization ready
- Environment variables for API URL switching

### Backend Optimization
- RAG engine caches embeddings (from Phase 1)
- Vector database indexes for fast retrieval
- LLM response caching (for similar errors)
- Async processing with FastAPI

### Network Optimization
- JSON compression (gzip enabled)
- Request batching where applicable
- Pagination ready for analysis history
- Lazy loading of results

## Production Deployment

### Frontend (Next.js)
```bash
# Build for production
npm run build

# Start production server
npm start

# Or deploy to Vercel (recommended)
vercel deploy
```

### Backend (FastAPI)
```bash
# Run with Gunicorn + Uvicorn
gunicorn backend.app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Environment Variables

**Frontend (.env.production):**
```env
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXTAUTH_URL=https://yourdomain.com
GITHUB_ID=<prod-github-id>
GITHUB_SECRET=<prod-github-secret>
NEXTAUTH_SECRET=<prod-secret>
```

**Backend (.env for gunicorn):**
```env
FASTAPI_ENV=production
CORS_ORIGINS=["https://yourdomain.com"]
VECTOR_DB_URL=postgresql://user:pass@host/db
```

## Monitoring & Debugging

### Frontend Debugging
```bash
# Enable debug logging
NEXT_DEBUG=* npm run dev

# Check auth state
# Open browser DevTools → Application → Cookies
# Look for "next-auth.session-token"
```

### Backend Debugging
```bash
# Enable debug mode
export FASTAPI_DEBUG=true
uvicorn backend.app.main:app --reload --log-level debug
```

### Check Logs
- Frontend: Browser console (F12)
- Backend: Terminal output
- System: Check `data/logs/` directory for saved logs

## Known Limitations & TODOs

### Phase 2.1 (Immediate)
- [ ] Integrate RAG engine with analysis endpoint
- [ ] Add database persistence (replace in-memory storage)
- [ ] Implement real GitHub PR creation
- [ ] Add request validation and error handling
- [ ] Write integration tests

### Phase 2.2 (Short-term)
- [ ] Token validation and expiry
- [ ] User-specific analysis history
- [ ] PR history and tracking
- [ ] Analysis result caching
- [ ] Email notifications

### Phase 2.3 (Medium-term)
- [ ] Repository selection interface
- [ ] Webhook integration for automatic analysis
- [ ] GitHub Actions integration
- [ ] Custom analysis configuration
- [ ] Performance analytics

## Support & Troubleshooting

### Check System Status
```bash
# Frontend
curl http://localhost:3000/

# Backend
curl http://localhost:8000/health

# Both
curl http://localhost:8000/api/analyses -H "Authorization: Bearer test"
```

### View Logs
```bash
# Backend startup logs
grep "FastAPI app created" /var/log/rag-backend.log

# Frontend runtime logs
# DevTools → Console tab
```

### Reset Development Environment
```bash
# Backend
pkill -f "uvicorn backend"
rm -rf backend/__pycache__

# Frontend
pkill -f "next dev"
rm -rf frontend/.next
npm install --force
```

## Resources

- [Next.js+FastAPI Integration](https://fastapi.tiangolo.com/deployment/concepts/)
- [NextAuth.js Documentation](https://next-auth.js.org)
- [FastAPI CORS Guide](https://fastapi.tiangolo.com/tutorial/cors/)
- [HTTP Headers Reference](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers)

## Next Steps

1. **Immediate**: Run `npm install` in frontend directory
2. **Setup**: Configure GitHub OAuth credentials
3. **Testing**: Follow "Testing the Integration" section
4. **Development**: Implement TODO endpoints with RAG integration
5. **Deployment**: Deploy to staging environment

## Summary

- ✅ Frontend structure created with Next.js + TypeScript + Tailwind
- ✅ GitHub OAuth authentication configured
- ✅ Analysis dashboard with forms and results display
- ✅ Backend API endpoints for frontend (analysis.py)
- ✅ API client utilities (lib/api.ts)
- ✅ TypeScript interfaces for type safety
- ✅ This integration guide

**Status:** Ready for testing and integration!
