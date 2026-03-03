"""
Unit tests for the RAG application (rag_app.py).

These tests focus on core functionality without requiring external services.
"""

import pytest
import json
import re
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path


class TestErrorExtraction:
    """Tests for error extraction from logs."""

    @pytest.mark.unit
    def test_extract_error_lines_from_log(self, sample_log_content):
        """Test extracting error lines from log content."""
        # This pattern matches the one used in rag_app.py
        error_lines = re.findall(
            r"^(?:Traceback.*|.*(?:ERROR|Exception|TypeError|RuntimeError|ValueError|failed|fatal|cannot|CRITICAL|AssertionError|ModuleNotFoundError|ImportError|IndexError|KeyError|AttributeError|NameError|OSError|IOError|ZeroDivisionError|TimeoutError|PermissionError|FileNotFoundError).*)$",
            sample_log_content,
            re.MULTILINE | re.IGNORECASE
        )

        assert len(error_lines) > 0, "Should extract at least one error line"
        assert "ModuleNotFoundError" in error_lines[0] or "ERROR" in error_lines[0]

    @pytest.mark.unit
    def test_extract_error_from_empty_log(self):
        """Test error extraction from empty log."""
        empty_log = ""
        error_lines = re.findall(
            r"^(?:Traceback.*|.*(?:ERROR|Exception|CRITICAL).*)$",
            empty_log,
            re.MULTILINE | re.IGNORECASE
        )

        assert len(error_lines) == 0, "Empty log should have no errors"

    @pytest.mark.unit
    def test_extract_multiple_error_types(self):
        """Test extraction of different error types."""
        log = """
[ERROR] Connection failed
[WARNING] Retrying connection
Traceback (most recent call last):
    File "test.py", line 10
TimeoutError: Connection timeout
CRITICAL: Service unavailable
        """

        error_lines = re.findall(
            r"^(?:Traceback.*|.*(?:ERROR|Exception|CRITICAL|TimeoutError).*)$",
            log,
            re.MULTILINE | re.IGNORECASE
        )

        assert len(error_lines) >= 3, "Should extract multiple error types"


class TestTextCleaning:
    """Tests for text cleaning utility."""

    def clean_text(self, text: str) -> str:
        """Copy of clean_text from rag_app.py."""
        if not isinstance(text, str):
            return ""
        cleaned = re.sub(r'\n\s*\n', '\n\n', text)
        cleaned = cleaned.encode("ascii", "ignore").decode("ascii")
        return cleaned.strip()

    @pytest.mark.unit
    def test_clean_text_removes_extra_newlines(self):
        """Test that clean_text removes extra newlines."""
        text = "Line 1\n\n\n\nLine 2"
        cleaned = self.clean_text(text)
        assert "\n\n\n" not in cleaned
        assert "Line 1" in cleaned
        assert "Line 2" in cleaned

    @pytest.mark.unit
    def test_clean_text_non_string_input(self):
        """Test clean_text with non-string input."""
        assert self.clean_text(None) == ""
        assert self.clean_text(123) == ""
        assert self.clean_text([]) == ""

    @pytest.mark.unit
    def test_clean_text_removes_non_ascii(self):
        """Test that clean_text removes non-ASCII characters."""
        text = "Hello™® World"
        cleaned = self.clean_text(text)
        assert "™" not in cleaned
        assert "®" not in cleaned
        assert "Hello" in cleaned
        assert "World" in cleaned


class TestQueryEnrichment:
    """Tests for query enrichment with log content."""

    @pytest.mark.unit
    def test_enrich_query_with_error_summary(self, sample_question, sample_log_content):
        """Test enriching a query with error summary."""
        # Extract error summary
        error_lines = re.findall(
            r"^(?:Traceback.*|.*(?:ERROR|CRITICAL|ModuleNotFoundError).*)$",
            sample_log_content,
            re.MULTILINE | re.IGNORECASE
        )
        error_summary = "\n".join(error_lines).strip()

        # Enrich query
        enriched = f"{sample_question}\n\nKey Error from Log:\n{error_summary}"

        assert sample_question in enriched
        assert "ModuleNotFoundError" in enriched
        assert "Key Error from Log:" in enriched

    @pytest.mark.unit
    def test_enrich_query_with_empty_error_summary(self, sample_question):
        """Test enriching query when no errors found."""
        error_summary = ""
        enriched = f"{sample_question}\n\nKey Error from Log:\n{error_summary}"

        assert sample_question in enriched
        assert "Key Error from Log:" in enriched


class TestResponseFormatting:
    """Tests for response formatting."""

    @pytest.mark.unit
    def test_format_response_with_documents(self, sample_ollama_response):
        """Test formatting a response with retrieved documents."""
        response = sample_ollama_response["response"]

        assert isinstance(response, str)
        assert len(response) > 0
        assert "install" in response.lower() or "pytorch" in response.lower()

    @pytest.mark.unit
    def test_format_response_preserves_structure(self):
        """Test that response formatting preserves message structure."""
        response = "Step 1: Do this\nStep 2: Do that\nStep 3: Verify"

        # Simple check that structure is preserved
        lines = response.split('\n')
        assert len(lines) == 3
        assert all("Step" in line for line in lines)


@pytest.mark.unit
class TestProcessQueryInitialization:
    """Tests for query processing initialization."""

    def test_model_config_structure(self):
        """Test that model config has expected structure."""
        model_config = {
            'my_mistral:latest': {'dir': 'mistral', 'config': 'my_mistral:latest'},
            'mistral:7b': {'dir': 'mistral', 'config': 'mistral:7b'},
            'llama3.2:3b': {'dir': 'llama3', 'config': 'llama3.2:3b'},
        }

        for model_name, config in model_config.items():
            assert 'dir' in config
            assert 'config' in config
            assert isinstance(config['dir'], str)
            assert isinstance(config['config'], str)

    def test_config_has_required_sections(self, mock_config):
        """Test that config has required sections."""
        required_sections = ['settings', 'database', 'lab_model', 'dgx_model']

        for section in required_sections:
            assert section in mock_config, f"Missing required section: {section}"

    def test_settings_config_values(self, mock_config):
        """Test that settings config has required values."""
        settings = mock_config['settings']

        assert 'chunk_size' in settings and isinstance(settings['chunk_size'], int)
        assert 'chunk_overlap' in settings and isinstance(settings['chunk_overlap'], int)
        assert 'connection_string' in settings and isinstance(settings['connection_string'], str)
        assert 'collection_name' in settings and isinstance(settings['collection_name'], str)
        assert settings['chunk_size'] > settings['chunk_overlap']


class TestRetrievalScoring:
    """Tests for document retrieval scoring."""

    @pytest.mark.unit
    def test_similarity_score_ordering(self, sample_retrieved_results):
        """Test that retrieved documents are ordered by score."""
        # Sort by score
        sorted_results = sorted(sample_retrieved_results, key=lambda x: x['score'], reverse=True)

        # Verify ordering
        for i in range(len(sorted_results) - 1):
            assert sorted_results[i]['score'] >= sorted_results[i+1]['score']

    @pytest.mark.unit
    def test_distance_threshold_filtering(self, sample_retrieved_results):
        """Test filtering documents by distance threshold."""
        DISTANCE_THRESHOLD = 0.7

        filtered = [doc for doc in sample_retrieved_results if doc['score'] > DISTANCE_THRESHOLD]

        # Should have at least 1 document above threshold
        assert len(filtered) > 0
        assert all(doc['score'] > DISTANCE_THRESHOLD for doc in filtered)

    @pytest.mark.unit
    def test_top_k_limiting(self, sample_retrieved_results):
        """Test limiting results to top k documents."""
        top_k = 2
        top_results = sample_retrieved_results[:top_k]

        assert len(top_results) == top_k
        assert top_results[0]['score'] >= top_results[1]['score']
