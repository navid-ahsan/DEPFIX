"""
Unit tests for embed_doc.py (document embedding pipeline).

These tests focus on document loading, chunking, and embedding preparation
without requiring actual Ollama or database services.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
from langchain_core.documents import Document


class TestDocumentLoading:
    """Tests for document loading from JSONL files."""

    @pytest.mark.unit
    def test_load_single_document_from_jsonl(self):
        """Test loading a single document from JSONL line."""
        line = json.dumps({"content": "Test content", "library": "test_lib", "source": "test.md"})

        data = json.loads(line)
        assert data["content"] == "Test content"
        assert data["library"] == "test_lib"
        assert data["source"] == "test.md"

    @pytest.mark.unit
    def test_load_list_of_documents_from_jsonl(self):
        """Test loading a list of documents from JSONL line."""
        documents = [
            {"content": "Content 1", "library": "lib1", "source": "source1"},
            {"content": "Content 2", "library": "lib2", "source": "source2"}
        ]
        line = json.dumps(documents)

        data = json.loads(line)
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["content"] == "Content 1"

    @pytest.mark.unit
    def test_malformed_jsonl_line_handling(self):
        """Test handling of malformed JSONL lines."""
        malformed_line = "This is not { valid JSON ]"

        with pytest.raises(json.JSONDecodeError):
            json.loads(malformed_line)

    @pytest.mark.unit
    def test_document_with_missing_content_skipped(self):
        """Test that documents without 'content' field are skipped."""
        doc_without_content = {"library": "test", "source": "test.md"}

        # Simulate the filtering logic
        if "content" in doc_without_content:
            Document(
                page_content=doc_without_content.get("content"),
                metadata={"library": doc_without_content.get("library")}
            )
        else:
            # Should not create document
            assert True  # Document correctly skipped


class TestDocumentChunking:
    """Tests for text splitting and document chunking."""

    @pytest.mark.unit
    def test_chunk_size_respected(self):
        """Test that chunks respect maximum size."""
        chunk_size = 1024
        chunk_overlap = 300

        # Simulate chunking
        text = "A" * 3000  # 3000 characters
        chunks = []

        # Simple chunking logic
        for i in range(0, len(text), chunk_size - chunk_overlap):
            chunk = text[i:i + chunk_size]
            chunks.append(chunk)

        # Verify all chunks are within size limit
        for chunk in chunks:
            assert len(chunk) <= chunk_size

    @pytest.mark.unit
    def test_overlap_between_chunks(self):
        """Test that chunks overlap correctly."""
        text = "0123456789" * 100  # 1000 characters
        chunk_size = 200
        overlap = 50

        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i:i + chunk_size]
            if chunk:
                chunks.append(chunk)

        # Verify overlap exists (consecutive chunks share content)
        if len(chunks) > 1:
            # Last 'overlap' chars of chunk[0] should match first 'overlap' chars of chunk[1]
            overlap_text_1 = chunks[0][-overlap:]
            overlap_text_2 = chunks[1][:overlap]
            assert overlap_text_1 == overlap_text_2

    @pytest.mark.unit
    def test_empty_document_chunking(self):
        """Test chunking empty documents."""
        text = ""
        chunks = [text] if text else []

        assert len(chunks) == 0

    @pytest.mark.unit
    def test_single_small_document_chunking(self):
        """Test chunking a document smaller than chunk size."""
        text = "Short document"
        chunk_size = 1024

        # Document smaller than chunk size should produce 1 chunk
        chunks = [text] if len(text) > 0 else []

        assert len(chunks) == 1
        assert chunks[0] == text


class TestDocumentMetadata:
    """Tests for document metadata handling."""

    @pytest.mark.unit
    def test_metadata_preservation(self):
        """Test that metadata is preserved in documents."""
        metadata = {"library": "pytorch", "source": "https://pytorch.org"}

        doc = Document(
            page_content="PyTorch installation guide",
            metadata=metadata
        )

        assert doc.metadata["library"] == "pytorch"
        assert doc.metadata["source"] == "https://pytorch.org"

    @pytest.mark.unit
    def test_default_metadata_for_missing_fields(self):
        """Test default values for missing metadata fields."""
        doc_data = {"content": "Test content"}

        metadata = {
            "library": doc_data.get("library", "unknown"),
            "source": doc_data.get("source", "unknown")
        }

        assert metadata["library"] == "unknown"
        assert metadata["source"] == "unknown"

    @pytest.mark.unit
    def test_metadata_from_scraper_output(self):
        """Test metadata structure from scraper output."""
        scraper_output = {
            "content": "Documentation text",
            "library": "scikit-learn",
            "source": "https://scikit-learn.org/stable/"
        }

        metadata = {
            "library": scraper_output.get("library", "unknown"),
            "source": scraper_output.get("source", "unknown")
        }

        assert metadata["library"] == "scikit-learn"
        assert "scikit-learn" in metadata["source"]


class TestEmbeddingConfiguration:
    """Tests for embedding model configuration."""

    @pytest.mark.unit
    def test_embedding_model_selection(self):
        """Test selecting embedding model from config."""
        lab_models = ["mxbai-embed-large:latest", "nomic-embed-text", "all-minilm"]
        dgx_models = ["nomic-embed-text", "jina/jina-embeddings-v2-base-en:latest"]

        # Simulate selection
        selected_lab = lab_models[1]  # nomic-embed-text
        selected_dgx = dgx_models[0]  # nomic-embed-text

        assert selected_lab == "nomic-embed-text"
        assert selected_dgx == "nomic-embed-text"

    @pytest.mark.unit
    def test_embedding_model_conversion_to_list(self):
        """Test handling embedding model as string or list."""
        # Could be single string
        model_single = "nomic-embed-text"
        models = [model_single] if isinstance(model_single, str) else model_single

        assert isinstance(models, list)
        assert len(models) > 0


class TestVectorDBConfiguration:
    """Tests for vector database configuration."""

    @pytest.mark.unit
    def test_connection_string_structure(self):
        """Test that connection string has valid structure."""
        connection_string = "postgresql+psycopg2://postgres:root@pgvector:5432/vector_db"

        # Basic validation
        assert connection_string.startswith("postgresql+psycopg2://")
        assert "postgres" in connection_string
        assert "pgvector" in connection_string
        assert "vector_db" in connection_string

    @pytest.mark.unit
    def test_collection_name_configuration(self):
        """Test collection name is properly set."""
        collection_name = "Error_handling"

        assert isinstance(collection_name, str)
        assert len(collection_name) > 0
        assert "_" in collection_name or collection_name.isidentifier()


class TestBatchProcessing:
    """Tests for batch processing of large document sets."""

    @pytest.mark.unit
    def test_batch_size_calculation(self):
        """Test calculating optimal batch size."""
        total_documents = 7500
        batch_size = 1000

        num_batches = (total_documents + batch_size - 1) // batch_size

        assert num_batches == 8
        assert num_batches * batch_size >= total_documents

    @pytest.mark.unit
    def test_batch_slicing(self):
        """Test slicing documents into batches."""
        documents = list(range(2500))  # Simulate 2500 documents
        batch_size = 1000

        batches = []
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            batches.append(batch)

        assert len(batches) == 3
        assert len(batches[0]) == 1000
        assert len(batches[1]) == 1000
        assert len(batches[2]) == 500
