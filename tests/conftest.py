"""
Pytest configuration and fixtures for RAG application tests.
"""

import pytest
import json
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict

# Fixtures for common test data and mocks


@pytest.fixture
def sample_log_content():
    """Sample error log for testing."""
    return """[2024-01-15 10:23:45] ERROR: Failed to import torch
Traceback (most recent call last):
  File "train.py", line 5, in <module>
    import torch
ModuleNotFoundError: No module named 'torch'
[2024-01-15 10:23:46] CRITICAL: PyTorch installation not detected
This is a critical error that prevents model training."""


@pytest.fixture
def sample_question():
    """Sample user question for testing."""
    return "How do I fix the ModuleNotFoundError for PyTorch?"


@pytest.fixture
def sample_retrieved_results():
    """Sample retrieved documents from vector DB."""
    return [
        {
            "page_content": "PyTorch Installation Guide:\n1. pip install torch torchvision\n2. Verify with: python -c 'import torch'",
            "metadata": {"library": "pytorch", "source": "https://pytorch.org/get-started"},
            "score": 0.85
        },
        {
            "page_content": "Common PyTorch Issues:\n- Missing CUDA drivers - Install from nvidia.com\n- Wrong Python version - Use Python 3.8+",
            "metadata": {"library": "pytorch", "source": "https://pytorch.org/docs"},
            "score": 0.78
        },
        {
            "page_content": "Virtual Environment Setup:\n1. python -m venv venv\n2. source venv/bin/activate\n3. pip install -r requirements.txt",
            "metadata": {"library": "general", "source": "https://docs.python.org"},
            "score": 0.65
        }
    ]


@pytest.fixture
def sample_ollama_response():
    """Sample response from Ollama LLM."""
    return {
        "response": "The ModuleNotFoundError indicates PyTorch is not installed. Here's the fix:\n1. Install PyTorch: pip install torch\n2. For GPU support, add CUDA libraries: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118\n3. Verify installation: python -c 'import torch'\nRefer to pytorch.org for environment-specific instructions.",
        "done": True,
        "context": [1, 2, 3, 4, 5],
        "total_duration": 987654321
    }


@pytest.fixture
def sample_eval_dataset():
    """Sample evaluation dataset."""
    return [
        {
            "question": "How to resolve PyTorch import error?",
            "log_excerpt": "[ERROR] ModuleNotFoundError: No module named 'torch'",
            "ground_truth": "Install PyTorch using pip install torch"
        },
        {
            "question": "How to fix CUDA version mismatch?",
            "log_excerpt": "[ERROR] CUDA version mismatch",
            "ground_truth": "Ensure CUDA drivers match PyTorch version"
        }
    ]


@pytest.fixture
def mock_config():
    """Mock configuration dictionary."""
    return {
        "settings": {
            "chunk_size": 1024,
            "chunk_overlap": 300,
            "connection_string": "postgresql+psycopg2://postgres:root@pgvector:5432/vector_db",
            "collection_name": "Error_handling"
        },
        "database": {
            "ollama": "http://ollama:11434"
        },
        "lab_model": {
            "embedding_models": ["mxbai-embed-large:latest", "nomic-embed-text"]
        },
        "dgx_model": {
            "embedding_models": ["nomic-embed-text", "jina/jina-embeddings-v2-base-en:latest"]
        }
    }


@pytest.fixture
def mock_ollama_client():
    """Mock Ollama client."""
    client = AsyncMock()
    client.generate = AsyncMock(return_value={
        "response": "This is a mocked response.",
        "done": True
    })
    return client


@pytest.fixture
def mock_pgvector():
    """Mock PGVector database client."""
    db = MagicMock()
    db.similarity_search_with_score = MagicMock(return_value=[
        (MagicMock(page_content="Doc 1 content"), 0.85),
        (MagicMock(page_content="Doc 2 content"), 0.75)
    ])
    db.similarity_search_with_relevance_scores = MagicMock(return_value=[
        (MagicMock(page_content="Doc 1 content"), 0.85),
        (MagicMock(page_content="Doc 2 content"), 0.75)
    ])
    return db


@pytest.fixture
def mock_embeddings():
    """Mock OllamaEmbeddings."""
    embeddings = MagicMock()
    embeddings.model = "nomic-embed-text"
    embeddings.embed_documents = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    embeddings.embed_query = AsyncMock(return_value=[0.1, 0.2, 0.3])
    return embeddings


@pytest.fixture
def mock_langchain_document():
    """Mock Document class from LangChain."""
    doc = MagicMock()
    doc.page_content = "Sample document content for testing"
    doc.metadata = {"source": "test.md", "chunk": 0}
    return doc


# Event loop fixture for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Pytest markers
def pytest_configure(config):
    """Register pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
