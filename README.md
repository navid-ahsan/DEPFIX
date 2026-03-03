# RAG CI/CD Error Analysis Framework

A local LLM-powered retrieval-augmented generation system for analyzing and resolving CI/CD pipeline errors.

## 📚 Documentation

All documentation has been organized in the `docs/` folder:

- **[README.md](docs/README.md)** - Project overview, features, and quick start
- **[DEVELOPMENT.md](docs/DEVELOPMENT.md)** - Architecture, development guide, and setup
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Production deployment (Docker, Kubernetes, standalone)
- **[PHASE1_STATUS.md](docs/PHASE1_STATUS.md)** - Phase 1 completion status
- **[TEST_RESULTS.md](docs/TEST_RESULTS.md)** - Test validation and metrics
- **[COMPLETION_CHECKLIST.md](docs/COMPLETION_CHECKLIST.md)** - Phase 1 deliverables
- **[IMPLEMENTATION_SUMMARY.md](docs/IMPLEMENTATION_SUMMARY.md)** - Implementation details
- **[SESSION_SUMMARY.md](docs/SESSION_SUMMARY.md)** - Recent work summary

## 🚀 Quick Start

```bash
# Setup environment
conda activate conda
cd /home/navid/project/socialwork

# Install dependencies
pip install -r requirements.txt

# Run validation script
bash scripts/phase1_validation.sh

# Start development server
export PYTHONPATH=/home/navid/project/socialwork
uvicorn backend.app.main:app --reload --port 8000
```

## 📁 Project Structure

```
socialwork/
├── docs/                 # All documentation
├── backend/             # FastAPI backend (Phase 1)
│   └── app/
│       ├── agents/      # 11 specialized agents
│       ├── api/         # REST endpoints
│       ├── core/        # Vector DB, RAG engine
│       └── utils/       # Utilities
├── tests/               # Test suite (58/60 passing)
├── scripts/             # Automation scripts
├── deploy/              # Deployment configs
├── archive/             # Legacy code (optional)
└── src/                 # Scraping utilities
```

## ✨ Phase 1 Status

- ✅ 11 specialized agents implemented
- ✅ OrchestratorAgent workflow coordination
- ✅ FastAPI backend with 31 routes
- ✅ Vector database abstraction layer
- ✅ Test suite: 58/60 passing (96.7%)
- ✅ Complete documentation
- ✅ CI/CD pipeline configured

## 🔗 File Links

- [Test Results](docs/TEST_RESULTS.md) - Detailed test report
- [Development Guide](docs/DEVELOPMENT.md) - Architecture overview
- [Deployment Options](docs/DEPLOYMENT.md) - Production setup

## 📞 Next Steps

For Phase 2 work (frontend, OAuth, code generation), see [DEVELOPMENT.md](docs/DEVELOPMENT.md#phase-2-planning).

---

**Last Updated**: March 2, 2026  
**Status**: Phase 1 Complete ✅
