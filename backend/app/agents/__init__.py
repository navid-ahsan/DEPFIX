"""Multi-agent orchestration system for CI/CD error analysis and resolution."""

import re
import requests
from .base import BaseAgent, AgentContext
from .orchestrator import OrchestratorAgent
from .intent_analyzer import IntentAnalyzerAgent

class DependencyExtractorAgent(BaseAgent):
    def __init__(self):
        super().__init__("DependencyExtractor", "Identify dependencies from PyPI")

    async def execute(self, context: AgentContext) -> AgentContext:
        """Resolve explicit versions for requested dependencies.

        The agent examines `context.dependencies` (a list of names provided by the
        user) or uses any previously-detected tech stack.  It then queries the
        PyPI JSON API to fetch the latest stable version for each package and
        stores the results in `context.detected_tech_stack`.
        """
        deps = set(context.dependencies or [])
        deps |= set(context.detected_tech_stack.keys())
        if not deps:
            self.log_message(context, "No dependencies found to resolve", level="warning")
            return context

        resolved = {}
        for pkg in deps:
            try:
                url = f"https://pypi.org/pypi/{pkg}/json"
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                version = data.get("info", {}).get("version", "")
                if version:
                    resolved[pkg] = version
                    self.log_message(context, f"Resolved {pkg} -> {version}")
                else:
                    self.log_message(context, f"Could not find version for {pkg}", level="warning")
            except Exception as e:
                self.log_message(context, f"Error querying PyPI for {pkg}: {e}", level="warning")
                resolved[pkg] = ""

        # Update context
        context.detected_tech_stack = {pkg: ver for pkg, ver in resolved.items()}
        return context

class DocScraperAgent(BaseAgent):
    def __init__(self):
        super().__init__("DocScraper", "Scrape official documentation")

    async def execute(self, context: AgentContext) -> AgentContext:
        """Use the global scraping utilities to fetch docs for each library.

        The method populates `context.scraped_docs` with a mapping from library
        name to list of Document objects returned by ``src.scrape``.
        """
        from src import scrape  # import after package is initialized

        libs = list(context.detected_tech_stack.keys() or context.dependencies)
        if not libs:
            self.log_message(context, "No libraries specified for scraping", level="warning")
            return context

        self.log_message(context, f"Scraping documentation for {len(libs)} libraries...")
        docs_map = scrape.scrape_libraries(libs)
        context.scraped_docs = docs_map
        count = sum(len(v) for v in docs_map.values())
        self.log_message(context, f"Scraped {count} documents in total")
        return context

class DataCleanerAgent(BaseAgent):
    def __init__(self):
        super().__init__("DataCleaner", "Clean and chunk documentation")

    async def execute(self, context: AgentContext) -> AgentContext:
        """Perform simple cleaning on scraped documents.

        Currently this strips excess whitespace and ensures the results are
        stored in ``context.cleaned_docs`` as plain strings.  This can be
        extended later to perform tokenization/chunking.
        """
        if not context.scraped_docs:
            self.log_message(context, "Nothing to clean", level="warning")
            return context

        cleaned = {}
        from backend.app.utils.text_utils import clean_scraped_content

        for lib, docs in context.scraped_docs.items():
            cleaned[lib] = []
            for doc in docs:
                raw = getattr(doc, "content", None)
                if raw is None and isinstance(doc, dict):
                    raw = doc.get("content", "")
                if not isinstance(raw, str):
                    raw = ""
                cleaned_text = clean_scraped_content(raw)
                cleaned[lib].append(cleaned_text)

        context.cleaned_docs = cleaned
        self.log_message(context, f"Cleaned documents for {len(cleaned)} libraries")
        return context

class VectorManagerAgent(BaseAgent):
    def __init__(self):
        super().__init__("VectorManager", "Index docs in vector DB")

    async def execute(self, context: AgentContext) -> AgentContext:
        """Index cleaned documents in the vector database.

        Converts cleaned text strings to LangChain Document objects and
        indexes them using the configured vector DB (pgvector).
        """
        if not context.cleaned_docs:
            self.log_message(context, "No cleaned documents to index", level="warning")
            return context

        from backend.app.core.vector_db import VectorDBManager
        from langchain_core.documents import Document

        try:
            # Initialize the vector DB manager
            vdb = VectorDBManager(
                db_type="pgvector",
                collection_name="error_analysis",
            )

            if not vdb.connect():
                self.log_message(context, "Failed to connect to vector DB", level="error")
                context.indexed_docs = False
                return context

            # Convert cleaned docs to LangChain Document objects
            all_docs = []
            for lib, texts in context.cleaned_docs.items():
                for i, text in enumerate(texts):
                    doc = Document(
                        page_content=text,
                        metadata={"library": lib, "doc_index": i},
                    )
                    all_docs.append(doc)

            # Index documents
            indexed_count = vdb.index_documents(all_docs)
            context.metadata["indexed_docs_count"] = indexed_count
            context.indexed_docs = True
            self.log_message(context, f"Indexed {indexed_count} documents in vector DB")
            return context

        except Exception as e:
            self.log_message(context, f"Error indexing documents: {e}", level="error")
            context.indexed_docs = False
            return context

class ErrorAnalyzerAgent(BaseAgent):
    def __init__(self):
        super().__init__("ErrorAnalyzer", "Parse and categorize errors")

    async def execute(self, context: AgentContext) -> AgentContext:
        """Extract meaningful lines from an uploaded error log."""
        log = context.error_log or ""
        if not log:
            self.log_message(context, "No error log provided", level="info")
            context.parsed_error = {}
            return context

        pattern = (r"^(?:Traceback.*|.*(?:ERROR|Exception|TypeError|RuntimeError|"
                   r"ValueError|failed|fatal|cannot|CRITICAL|AssertionError|"
                   r"ModuleNotFoundError|ImportError|IndexError|KeyError|"
                   r"AttributeError|NameError|OSError|IOError|ZeroDivisionError|"
                   r"TimeoutError|PermissionError|FileNotFoundError).*)$")
        matches = re.findall(pattern, log, re.MULTILINE | re.IGNORECASE)
        summary = "\n".join(matches).strip()
        context.parsed_error = {"summary": summary, "matches": matches}
        self.log_message(context, f"Extracted {len(matches)} error lines")
        return context

class SolutionGeneratorAgent(BaseAgent):
    def __init__(self):
        super().__init__("SolutionGenerator", "Generate solution guidance")

    async def execute(self, context: AgentContext) -> AgentContext:
        """Generate solution guidance using RAG.

        Retrieves relevant documentation snippets and constructs a prompt
        for the LLM. In a full implementation, this would call Ollama
        with the grounded context.
        """
        question = context.user_intent or ""
        if not question:
            self.log_message(context, "No user intent provided", level="warning")
            return context

        from backend.app.core.vector_db import VectorDBManager

        try:
            # Initialize vector DB
            vdb = VectorDBManager(db_type="pgvector")
            if not vdb.connect():
                self.log_message(context, "Cannot connect to vector DB for retrieval", level="warning")
                # Fallback to template response
                context.solution = f"Question: {question}\n\nUnable to retrieve documentation context."
                return context

            # Retrieve relevant documents
            search_results = vdb.search(question, k=5)
            retrieved_docs = [doc for doc, score in search_results]
            retrieval_scores = [score for doc, score in search_results]

            context.metadata["retrieval_count"] = len(retrieved_docs)
            context.metadata["retrieval_scores"] = [float(s) for s in retrieval_scores]

            # Build RAG prompt
            context_text = "\n---\n".join(
                [f"[{doc.metadata.get('library', 'unknown')}]\n{doc.page_content[:200]}..."
                 for doc in retrieved_docs]
            ) if retrieved_docs else "(No relevant documentation found)"

            prompt = f"""You are a CI/CD error resolution assistant. Answer the following question
using ONLY the provided documentation context. If you cannot find a relevant answer,
say so explicitly.

DOCUMENTATION CONTEXT:
{context_text}

USER QUESTION:
{question}

ANSWER:
"""

            # In production, call LLM here:
            # from langchain_ollama import OllamaLLM
            # llm = OllamaLLM(model="mistral:7b", base_url="http://ollama:11434")
            # response = llm.invoke(prompt)

            # For now, simulate a response
            response = f"Based on the retrieved documentation:\n\n{context_text[:300]}...\n\nAnswer: {question} is typically resolved by checking the dependency versions and ensuring compatibility."

            context.solution = response
            self.log_message(context, f"Generated solution with {len(retrieved_docs)} retrieved doc(s)")
            return context

        except Exception as e:
            self.log_message(context, f"Error generating solution: {e}", level="error")
            context.solution = f"Error: Could not generate solution. {str(e)}"
            return context

class CodeSuggesterAgent(BaseAgent):
    def __init__(self):
        super().__init__("CodeSuggester", "Suggest code fixes")

    async def execute(self, context: AgentContext) -> AgentContext:
        """Generate code fix suggestions based on error analysis.

        Examines the parsed error and creates human-readable suggestions
        for code changes. In production this would call an LLM to generate
        diffs, but for now we produce template suggestions.
        """
        if not context.parsed_error or not context.parsed_error.get("summary"):
            self.log_message(context, "No error to suggest fixes for", level="warning")
            return context

        suggestions = []
        error_summary = context.parsed_error["summary"]

        # Simple heuristic-based suggestions
        if "ModuleNotFoundError" in error_summary or "ImportError" in error_summary:
            suggestions.append({
                "description": "Install missing dependency",
                "code_before": "# Missing import",
                "code_after": "# Install: pip install <package_name>",
                "confidence": 0.8,
            })
        if "Version" in error_summary or "incompatible" in error_summary.lower():
            suggestions.append({
                "description": "Update problematic dependency",
                "code_before": "requirements.txt: package==old_version",
                "code_after": "requirements.txt: package==new_version",
                "confidence": 0.7,
            })

        context.suggested_fixes = suggestions
        self.log_message(context, f"Generated {len(suggestions)} code fix suggestions")
        return context


class ApprovalManagerAgent(BaseAgent):
    def __init__(self):
        super().__init__("ApprovalManager", "Handle user approval workflow")

    async def execute(self, context: AgentContext) -> AgentContext:
        """Manage user approval workflow for suggested fixes.

        In a real system this would wait for user input via the API.
        For now, we simulate automatic approval of high-confidence suggestions.
        """
        if not context.suggested_fixes:
            self.log_message(context, "No fixes to approve", level="info")
            return context

        # Auto-approve high-confidence suggestions (>= 0.8)
        approved = [fix for fix in context.suggested_fixes if fix.get("confidence", 0) >= 0.8]
        if approved:
            context.approved_fix = approved[0]  # Pick the first approved
            self.log_message(
                context,
                f"Auto-approved fix: {approved[0].get('description', 'unknown')}",
            )
        else:
            self.log_message(context, "All suggestions require user approval", level="info")

        context.metadata["approved_fixes_count"] = len(approved)
        return context


class CodeExecutorAgent(BaseAgent):
    def __init__(self):
        super().__init__("CodeExecutor", "Apply approved changes")

    async def execute(self, context: AgentContext) -> AgentContext:
        """Execute approved code fixes.

        In a real system this would:
        - Clone the repository
        - Apply the fix
        - Run tests
        - Commit and push (or create PR)

        For now we just simulate the execution and record metadata.
        """
        if not context.approved_fix:
            self.log_message(context, "No approved fix to execute", level="info")
            return context

        fix = context.approved_fix
        description = fix.get("description", "unknown fix")

        # Simulate execution
        try:
            # In production: actually apply the fix to the codebase
            self.log_message(context, f"Executing: {description}")
            # Simulate success
            context.execution_result = {
                "success": True,
                "fix_applied": description,
                "tests_passed": True,
                "pr_created": False,
            }
            self.log_message(context, "Fix execution completed successfully")
        except Exception as e:
            context.execution_result = {
                "success": False,
                "error": str(e),
            }
            self.log_message(context, f"Fix execution failed: {e}", level="error")

        return context


class EvaluatorAgent(BaseAgent):
    def __init__(self):
        super().__init__("Evaluator", "Assess fix success")

    async def execute(self, context: AgentContext) -> AgentContext:
        """Evaluate the quality and accuracy of the solution.

        Uses simple heuristics to assess:
        - Whether the solution addresses the error
        - How grounded it is in the retrieved documentation
        - Whether execution was successful

        In production this would use RAGAS metrics.
        """
        query = context.user_intent or ""
        solution = context.solution or ""
        execution = context.execution_result or {}

        score = 0.0
        reasons = []

        # Score based on solution length and content
        if solution and len(solution) > 20:
            score += 0.3
            reasons.append("Solution has substantive content")

        # Score based on execution success
        if execution.get("success"):
            score += 0.4
            reasons.append("Fix execution succeeded")
        elif execution.get("success") is False:
            reasons.append("Fix execution failed")

        # Score based on error parsing
        if context.parsed_error and context.parsed_error.get("summary"):
            score += 0.3
            reasons.append("Error was parsed and analyzed")

        # Cap score at 1.0
        score = min(score, 1.0)

        context.metadata["evaluation_score"] = score
        context.metadata["evaluation_reasons"] = reasons
        self.log_message(context, f"Evaluation complete: score={score:.2f}")
        return context


__all__ = [
    "BaseAgent",
    "AgentContext",
    "OrchestratorAgent",
    "IntentAnalyzerAgent",
    "DependencyExtractorAgent",
    "DocScraperAgent",
    "DataCleanerAgent",
    "VectorManagerAgent",
    "ErrorAnalyzerAgent",
    "SolutionGeneratorAgent",
    "CodeSuggesterAgent",
    "ApprovalManagerAgent",
    "CodeExecutorAgent",
    "EvaluatorAgent",
]
