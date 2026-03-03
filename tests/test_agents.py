"""Unit tests for agent implementations in backend/app/agents.

We focus on the small, deterministic behaviors that do not require external
services.  Network calls (PyPI, scraping) are mocked so that tests remain
fast and reliable.
"""

import pytest
from unittest.mock import patch, MagicMock

from backend.app.agents import (
    DependencyExtractorAgent,
    DocScraperAgent,
    DataCleanerAgent,
    VectorManagerAgent,
    ErrorAnalyzerAgent,
    SolutionGeneratorAgent,
    AgentContext,
)


@pytest.mark.unit
class TestDependencyExtractorAgent:

    @pytest.mark.asyncio
    async def test_resolves_versions_with_mock(self):
        agent = DependencyExtractorAgent()
        ctx = AgentContext(dependencies=["foo"])

        fake_resp = MagicMock()
        fake_resp.json.return_value = {"info": {"version": "9.9.9"}}
        fake_resp.raise_for_status.return_value = None

        with patch("requests.get", return_value=fake_resp):
            new_ctx = await agent.execute(ctx)

        assert "foo" in new_ctx.detected_tech_stack
        assert new_ctx.detected_tech_stack["foo"] == "9.9.9"


@pytest.mark.unit
class TestDocScraperAgent:
    @pytest.mark.asyncio
    async def test_scrapes_and_populates_context(self):
        agent = DocScraperAgent()
        ctx = AgentContext()
        ctx.detected_tech_stack = {"foo": "1.0.0"}

        fake_docs = {"foo": [MagicMock(content="abc"), MagicMock(content="def")]}
        with patch("src.scrape.scrape_libraries", return_value=fake_docs) as mock_scrape:
            new_ctx = await agent.execute(ctx)

        assert "foo" in new_ctx.scraped_docs
        assert len(new_ctx.scraped_docs["foo"]) == 2
        mock_scrape.assert_called_once_with(["foo"])


@pytest.mark.unit
class TestDataCleanerAgent:
    @pytest.mark.asyncio
    async def test_cleans_documents(self):
        agent = DataCleanerAgent()
        ctx = AgentContext()
        # create simple objects with .content attribute
        class D:
            def __init__(self, c):
                self.content = c
        ctx.scraped_docs = {"lib": [D(" foo \nbar  "), {"content": "baz"}]}

        new_ctx = await agent.execute(ctx)
        assert "lib" in new_ctx.cleaned_docs
        assert any("foo" in txt for txt in new_ctx.cleaned_docs["lib"])


@pytest.mark.unit
class TestVectorManagerAgent:
    @pytest.mark.asyncio
    async def test_indexes_documents(self):
        agent = VectorManagerAgent()
        ctx = AgentContext()
        ctx.cleaned_docs = {"lib": ["a", "b", "c"]}
        new_ctx = await agent.execute(ctx)
        assert new_ctx.indexed_docs
        assert new_ctx.metadata.get("indexed_docs_count") == 3


@pytest.mark.unit
class TestErrorAnalyzerAgent:
    @pytest.mark.asyncio
    async def test_parses_error_log(self):
        agent = ErrorAnalyzerAgent()
        ctx = AgentContext(error_log="[ERROR] something failed\nTraceback (most recent call)")
        new_ctx = await agent.execute(ctx)
        assert "summary" in new_ctx.parsed_error
        assert "ERROR" in new_ctx.parsed_error["summary"]

    @pytest.mark.asyncio
    async def test_handles_empty_log(self):
        agent = ErrorAnalyzerAgent()
        ctx = AgentContext(error_log="")
        new_ctx = await agent.execute(ctx)
        assert new_ctx.parsed_error == {}


@pytest.mark.unit
class TestSolutionGeneratorAgent:
    @pytest.mark.asyncio
    async def test_generates_solution_template(self):
        agent = SolutionGeneratorAgent()
        ctx = AgentContext(user_intent="Fix this issue")
        ctx.parsed_error = {"summary": "Something broke"}
        new_ctx = await agent.execute(ctx)
        assert "issue" in new_ctx.solution.lower()
        assert "something broke" in new_ctx.solution.lower()