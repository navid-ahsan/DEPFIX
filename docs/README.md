# Implementing a Local LLM with Retrieval-Augmented Generation on a CI/CD Pipeline

A **closed-source**, local framework for accelerating CI/CD error resolution through
Retrieval-Augmented Generation (RAG). This system enables developers to analyze error
logs, resolve integration issues faster, and ground LLM responses in project-specific
and dependency-specific documentation—all without leaving your infrastructure.

## Key Features

- **Multi-Agent Architecture**: Modular components for intent analysis, dependency resolution,
  documentation scraping, error parsing, and solution generation.
- **Local-First Design**: All processing stays on your machine; no external API calls or
  cloud snapshots.
- **Dynamic Documentation Scraping**: Automatically fetches and indexes the latest official
  docs for dependencies (PyTorch, MONAI, scikit-learn, etc.).
- **Flexible Vector DB**: Support for pgvector, ChromaDB, Milvus, and others.
- **User-Selectable LLM**: Run locally with Ollama; choose from Mistral, Llama, Gemma, etc.
- **Drag-and-Drop UI**: Submit CI/CD logs via browser or API.
- **GitHub/GitLab Integration**: Authenticate securely with OAuth2.
- **Evaluation Metrics**: Minimize hallucinations using RAGAS metrics (answer relevancy,
  faithfulness, context precision, context recall).

## Quick Start

### Prerequisites

- Python 3.9+
- Docker & Docker Compose (for PostgreSQL + Ollama)
- ~4GB+ available VRAM (for local LLM inference)

### Development Setup

```bash
# Clone and enter the repo
cd /path/to/socialwork

# Create Python environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Start services (PostgreSQL + Ollama)
docker-compose up -d

# Run the FastAPI backend
cd backend/app
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`, with OpenAPI docs at `/docs`.

### CLI RAG Application

For command-line evaluation and testing:

```bash
cd src

# Basic query with CI/CD error log
python rag_app.py --env lab_model --model mistral:7b

# Run evaluation suite
python rag_app.py --env lab_model --model mistral:7b --evaluate
```

Supported models:
- Lab: `mistral:7b`, `llama3.2:3b`, `my_mistral:latest`
- DGX: `gemma3:27b`, `llama4`, `my_llama4:latest`

## Project Structure

```
.
├── backend/                  # FastAPI application
│   └── app/
│       ├── main.py          # App factory & middleware
│       ├── config.py        # Settings management
│       ├── agents/          # Multi-agent orchestrator
│       │   ├── base.py      # BaseAgent & AgentContext
│       │   ├── intent_analyzer.py
│       │   ├── orchestrator.py
│       │   └── __init__.py  # Agent implementations
│       ├── api/             # Endpoint routers
│       │   ├── rag.py       # /api/rag/* endpoints
│       │   ├── logs.py      # /api/logs/* endpoints
│       │   ├── dependencies.py  # /api/dependencies/* endpoints
│       │   └── integrations.py  # OAuth2 flows
│       ├── core/            # Core business logic
│       │   ├── rag_engine.py
│       │   └── error_extractor.py
│       └── models/          # SQLAlchemy models
├── src/                     # Standalone CLI tools
│   ├── rag_app.py          # Main RAG CLI application
│   ├── scrape.py           # Documentation scraping utilities
│   ├── embed_doc.py        # Document embedding & indexing
│   ├── scrape2.py          # Alternative scraper (legacy)
│   └── config.toml         # Configuration file
├── data/
│   ├── documents/          # Scraped JSONL docs
│   ├── logs/               # Sample CI/CD error logs
│   ├── outputs/            # Query results
│   └── inputs/             # User input JSON
├── tests/
│   ├── test_rag_app.py
│   ├── test_embed_doc.py
│   ├── test_server.py
│   ├── test_agents.py      # Agent workflow tests
│   └── conftest.py
├── deploy/                 # K8s/Helm configurations
├── ollama_build/           # Modelfile definitions
└── bash/                   # Utility scripts

```

## API Usage

### Submit a RAG Query

```bash
curl -X POST http://localhost:8000/api/rag/query \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'query_text=How do I fix PyTorch version conflicts?' \
  -d 'dependencies=torch&dependencies=torchvision' \
  -d 'log_id=&intent=guidance'
```

**Response:**

```json
{
  "success": true,
  "query_id": "query_1234567890.123",
  "query": "How do I fix PyTorch version conflicts?",
  "dependencies": ["torch", "torchvision"],
  "intent": "guidance",
  "response": "Based on the documentation...",
  "parsed_error": {...},
  "scraped_libraries": ["torch", "torchvision"],
  "metadata": {...},
  "generated_at": "2026-03-02T12:34:56.789Z"
}
```

### Upload and Analyze a Log File

```bash
# Endpoint to be implemented in Phase 2
POST /api/logs/upload
Content-Type: multipart/form-data

key: error.log
value: <binary log file>
```

## Multi-Agent Workflow

The framework orchestrates seven specialized agents:

1. **IntentAnalyzer**: Parses user query, extracts tech stack hints, classifies intent
   (guidance vs. automatic fix).
2. **DependencyExtractor**: Resolves dependency versions via PyPI API.
3. **DocScraper**: Crawls official documentation for selected libraries using `src.scrape`.
4. **DataCleaner**: Chunks and cleans documentation text, removes code artifacts.
5. **VectorManager**: Indexes cleaned documents in pgvector (or alternative vector DB).
6. **ErrorAnalyzer**: Extracts and categorizes error lines from log files.
7. **SolutionGenerator**: Uses LLM with RAG context to generate guidance or code suggestions.

Each agent extends `BaseAgent` and plugs into `OrchestratorAgent` for coordinated execution.

## Testing

Run the full unit test suite:

```bash
pytest -m unit

# Run specific test class
pytest tests/test_agents.py::TestDependencyExtractorAgent -v

# Run with coverage
pytest --cov=backend --cov=src tests/
```

### Test Categories

- **Unit Tests** (`@pytest.mark.unit`): Fast, no external services.
- **Integration Tests** (tagged): Require running Docker services.
- **E2E Tests** (tagged): Full workflow including LLM inference.

## Configuration

The system is configured through:

- **Environment variables** (prefixed `LLM_`, `VECTORDB_`, etc.)
- **`.env` file** in the project root
- **`src/config.toml`** (TOML file with database and model settings)
- **Backend settings** in `backend/app/config.py` (Pydantic BaseSettings)

### Example `.env`

```
# LLM Configuration
LLM_TYPE=ollama
LLM_OLLAMA_HOST=http://ollama:11434
LLM_OLLAMA_MODEL=mistral:7b
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=2048

# Vector DB Configuration
VECTORDB_TYPE=pgvector
VECTORDB_POSTGRES_URL=postgresql+psycopg2://postgres:root@localhost:5432/vector_db
VECTORDB_COLLECTION_NAME=Error_handling
VECTORDB_CHUNK_SIZE=1024
VECTORDB_CHUNK_OVERLAP=300
VECTORDB_SEARCH_K=5

# GitHub Integration (optional)
GITHUB_ENABLED=false
GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_client_secret
```

## Evaluation

The framework uses **RAGAS** (Retrieval-Augmented Generation Assessment) to measure:

- **Answer Relevancy**: How well the response addresses the query.
- **Faithfulness**: Whether the answer is grounded in retrieved documents.
- **Context Precision**: Relevance of retrieved context snippets.
- **Context Recall**: Coverage of all relevant context in the retrieved set.

Run evaluation on a test dataset:

```bash
python src/rag_app.py --env lab_model --model mistral:7b --evaluate
```

Results are saved to `data/outputs/query_results_rag_vs_non_rag.txt`.

## Roadmap

### Phase 1 (Current)
- ✅ Multi-agent architecture and orchestrator
- ✅ Document scraping for 10+ libraries
- ✅ FastAPI backend with RAG endpoint
- ✅ PGVector integration
- 🔄 Unit tests for all agents
- 🔄 RAGAS evaluation suite

### Phase 2
- [ ] Drag-and-drop UI (React/Vue frontend)
- [ ] Log file upload and processing
- [ ] Code suggestion and diff generation
- [ ] Approval workflow for automatic fixes
- [ ] GitHub/GitLab PR integration

### Phase 3
- [ ] ChatDB support (alternative to pgvector)
- [ ] Milvus vector DB support
- [ ] Fine-tuned local models (LoRA, QLoRA)
- [ ] Batch evaluation dashboard
- [ ] Advanced monitoring and tracing

## License

Proprietary / Closed Source

## Support & Contribution

This is a closed-source project. For issues, questions, or contributions, please contact
the development team via internal channels.

---

**Last Updated**: March 2, 2026 | **Version**: 0.1.0
