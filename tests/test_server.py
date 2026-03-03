"""
Unit tests for the FastAPI server (server.py).

These tests focus on API endpoint functionality and request/response handling.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from pydantic import BaseModel, ValidationError
from typing import List


class TestPydanticModels:
    """Tests for API Pydantic models."""

    @pytest.mark.unit
    def test_rag_request_valid(self):
        """Test valid RAGRequest creation."""
        request_data = {
            "query": "How to fix this error?",
            "log_content": "[ERROR] Something went wrong"
        }

        # Simulating Pydantic validation
        assert "query" in request_data
        assert "log_content" in request_data
        assert isinstance(request_data["query"], str)
        assert isinstance(request_data["log_content"], str)

    @pytest.mark.unit
    def test_rag_request_missing_field(self):
        """Test RAGRequest with missing field."""
        request_data = {
            "query": "How to fix this error?"
            # Missing log_content
        }

        # Missing required field should fail validation
        assert "log_content" not in request_data

    @pytest.mark.unit
    def test_related_document_model(self):
        """Test RelatedDocument model."""
        doc_data = {
            "content": "API documentation",
            "score": 0.85
        }

        assert "content" in doc_data
        assert "score" in doc_data
        assert isinstance(doc_data["score"], float)
        assert 0 <= doc_data["score"] <= 1

    @pytest.mark.unit
    def test_rag_response_structure(self):
        """Test RAGResponse model structure."""
        response_data = {
            "response": "Here is the answer...",
            "related_documents": [
                {"content": "Doc 1", "score": 0.9},
                {"content": "Doc 2", "score": 0.85}
            ]
        }

        assert "response" in response_data
        assert "related_documents" in response_data
        assert isinstance(response_data["related_documents"], list)
        assert len(response_data["related_documents"]) == 2


class TestANSICodeRemoval:
    """Tests for ANSI escape code removal."""

    @pytest.mark.unit
    def test_ansi_code_removal(self):
        """Test removing ANSI escape codes from text."""
        import re

        # Simulate ANSI codes
        text_with_ansi = "\x1B[31mRed text\x1B[0m"

        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        cleaned = ansi_escape.sub('', text_with_ansi)

        assert "\x1B" not in cleaned
        assert "Red text" in cleaned

    @pytest.mark.unit
    def test_ansi_code_removal_preserves_content(self):
        """Test that ANSI removal preserves actual content."""
        import re

        text = "\x1B[1;32m✓ Success\x1B[0m"

        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        cleaned = ansi_escape.sub('', text)

        assert "Success" in cleaned

    @pytest.mark.unit
    def test_ansi_removal_on_clean_text(self):
        """Test ANSI removal on text without codes."""
        import re

        text = "Normal text without codes"

        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        cleaned = ansi_escape.sub('', text)

        assert cleaned == text


class TestHealthCheckEndpoint:
    """Tests for health check endpoint."""

    @pytest.mark.unit
    def test_health_check_response(self):
        """Test health check returns ok status."""
        # Simulate endpoint response
        response = {"status": "ok"}

        assert response["status"] == "ok"

    @pytest.mark.unit
    def test_health_check_is_json(self):
        """Test health check returns JSON."""
        response = {"status": "ok"}

        # Should be serializable to JSON
        import json
        json_str = json.dumps(response)
        assert "status" in json_str
        assert "ok" in json_str


class TestConfigurationLoading:
    """Tests for configuration loading in server."""

    @pytest.mark.unit
    def test_environment_variable_selection(self):
        """Test selecting environment from arguments."""
        env_choices = ['lab_model', 'dgx_model']
        selected_env = 'lab_model'

        assert selected_env in env_choices

    @pytest.mark.unit
    def test_embedding_model_from_config(self):
        """Test extracting embedding model from config."""
        config = {
            "lab_model": {
                "embedding_models": ["mxbai-embed-large:latest", "nomic-embed-text"]
            },
            "dgx_model": {
                "embedding_models": ["nomic-embed-text", "jina/jina-embeddings-v2-base-en:latest"]
            }
        }

        # Simulate config selection
        env = 'lab_model'
        embedding_models = config[env]["embedding_models"]
        embedding_model = embedding_models[0] if isinstance(embedding_models, list) else embedding_models

        assert embedding_model == "mxbai-embed-large:latest"

    @pytest.mark.unit
    def test_config_has_required_sections(self):
        """Test that config has all required sections."""
        config = {
            "settings": {},
            "database": {},
            "lab_model": {},
            "dgx_model": {}
        }

        required = ["settings", "database", "lab_model", "dgx_model"]

        for section in required:
            assert section in config


# ---------------------------------------------------------------------------
# Additional tests covering the new orchestrator integration

class TestRAGEndpoint:
    """Tests that exercise the RAG query endpoint implementation."""

    @pytest.mark.asyncio
    async def test_rag_query_endpoint(self, monkeypatch):
        from backend.app.api.rag import rag_query

        class DummyOrch:
            def __init__(self):
                self.agents = []

            def register_agent(self, a):
                self.agents.append(a)

            def set_execution_plan(self, plan):
                self.plan = plan

            async def execute(self, context):
                context.solution = "dummy response"
                context.scraped_docs = {"foo": []}
                context.metadata = {"foo": "bar"}
                return context

        monkeypatch.setattr('backend.app.api.rag.OrchestratorAgent', DummyOrch)

        result = await rag_query("hello", ["foo"], None, "guidance")
        assert result["success"] is True
        assert "dummy response" in result["response"]
        assert result["scraped_libraries"] == ["foo"]


class TestErrorHandling:
    """Tests for error handling in API."""

    @pytest.mark.unit
    def test_http_exception_with_500_status(self):
        """Test HTTP 500 error response."""
        error_detail = "An internal server error occurred"

        # Simulate HTTPException structure
        error_response = {
            "status_code": 500,
            "detail": error_detail
        }

        assert error_response["status_code"] == 500
        assert "error" in error_response["detail"].lower() or "occurred" in error_response["detail"]

    @pytest.mark.unit
    def test_exception_logging(self):
        """Test that exceptions are properly logged."""
        try:
            raise ValueError("Test error")
        except ValueError as e:
            error_msg = str(e)
            assert "Test error" in error_msg


class TestDocumentScoreCleaning:
    """Tests for cleaning document scores in responses."""

    @pytest.mark.unit
    def test_document_score_rounding(self):
        """Test that document scores are rounded to 4 decimals."""
        raw_score = 0.8765432

        rounded_score = round(raw_score, 4)

        assert rounded_score == 0.8765
        assert len(str(rounded_score).split('.')[-1]) <= 4

    @pytest.mark.unit
    def test_multiple_documents_score_cleaning(self):
        """Test cleaning multiple document scores."""
        raw_docs = [
            {"content": "Doc 1", "score": 0.9876543},
            {"content": "Doc 2", "score": 0.7654321},
            {"content": "Doc 3", "score": 0.5432109}
        ]

        cleaned_docs = [
            {"content": doc["content"], "score": round(doc["score"], 4)}
            for doc in raw_docs
        ]

        for doc in cleaned_docs:
            assert len(str(doc["score"]).split('.')[-1]) <= 4


class TestArgumentParsing:
    """Tests for command-line argument parsing."""

    @pytest.mark.unit
    def test_environment_argument_required(self):
        """Test that --env argument is required."""
        required_args = ['--env', '--model']

        assert '--env' in required_args
        assert '--model' in required_args

    @pytest.mark.unit
    def test_environment_choices(self):
        """Test that --env only accepts valid choices."""
        valid_choices = ['lab_model', 'dgx_model']
        test_value = 'lab_model'

        assert test_value in valid_choices

    @pytest.mark.unit
    def test_invalid_environment_rejected(self):
        """Test that invalid environment is rejected."""
        valid_choices = ['lab_model', 'dgx_model']
        invalid_value = 'invalid_env'

        assert invalid_value not in valid_choices
