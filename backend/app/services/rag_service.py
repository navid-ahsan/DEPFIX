"""RAG (Retrieval-Augmented Generation) service for error analysis and fix generation."""

import json
import logging
import os
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid
import re

from sqlalchemy.orm import Session
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document
import requests

from backend.app.models.database import Query, Log, Dependency, VectorStore
from backend.app.services.embedding_service import PGVectorStorage

logger = logging.getLogger(__name__)


class DocumentRetriever:
    """Retrieves relevant documentation chunks for error analysis."""

    def __init__(self):
        self.ollama_url = os.environ.get("LLM_OLLAMA_HOST", "http://localhost:11434")
        try:
            self.embeddings = OllamaEmbeddings(
                model="nomic-embed-text",
                base_url=self.ollama_url,
            )
            self.is_available = True
        except Exception as e:
            logger.warning(f"Embeddings not available: {e}")
            self.is_available = False
        self.pg_storage = PGVectorStorage()

    async def retrieve_relevant_docs_async(
        self,
        error_text: str,
        db: Session,
        dependency_names: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Async wrapper — runs blocking embedding + pgvector search in a thread."""
        return await asyncio.to_thread(
            self.retrieve_relevant_docs, error_text, db, dependency_names, top_k
        )

    def retrieve_relevant_docs(
        self,
        error_text: str,
        db: Session,
        dependency_names: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant documentation chunks for an error."""

        if not self.is_available:
            logger.warning("Embeddings unavailable, returning mock results")
            return self._mock_retrieve(error_text, db, dependency_names, top_k)

        try:
            # Embed the error text
            error_embedding = self.embeddings.embed_query(error_text)

            # Try real pgvector similarity search first
            if self.pg_storage._ready:
                results = self.pg_storage.similarity_search(
                    embedding=error_embedding,
                    dependency_names=dependency_names,
                    top_k=top_k,
                )
                if results:
                    logger.info(f"Retrieved {len(results)} chunks from pgvector")
                    return results
                else:
                    logger.warning("pgvector returned 0 results — docs may not be embedded yet")

            # Fallback: keyword-based search from SQLite docs_cache
            return self._keyword_retrieve(error_text, db, dependency_names, top_k)

        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return self._mock_retrieve(error_text, db, dependency_names, top_k)

    def _keyword_retrieve(
        self,
        error_text: str,
        db: Session,
        dependency_names: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Fallback keyword-based retrieval from SQLite docs_cache."""
        if dependency_names:
            deps = db.query(Dependency).filter(
                Dependency.name.in_(dependency_names)
            ).all()
        else:
            deps = db.query(Dependency).filter(
                Dependency.is_active == True
            ).limit(10).all()

        relevant_docs = []
        for dep in deps:
            if dep.docs_cache:
                try:
                    docs_data = dep.docs_cache
                    if isinstance(docs_data, str):
                        docs_data = json.loads(docs_data)
                    snippets = self._extract_relevant_snippets(error_text, docs_data)
                    for snippet in snippets[:2]:
                        relevant_docs.append({
                            "dependency": dep.name,
                            "content": snippet,
                            "relevance_score": 0.5,
                            "source": dep.documentation_url or "",
                        })
                except Exception:
                    pass
        return relevant_docs[:top_k] if relevant_docs else self._mock_retrieve(error_text, db, dependency_names, top_k)

    def _extract_relevant_snippets(self, error_text: str, docs_data: Dict) -> List[str]:
        """Extract snippets from documentation relevant to the error."""
        snippets = []
        error_keywords = self._extract_keywords(error_text)
        if isinstance(docs_data, dict):
            for key, value in docs_data.items():
                if isinstance(value, str):
                    if any(kw.lower() in value.lower() for kw in error_keywords):
                        snippets.append(value[:500])
        return snippets if snippets else [str(docs_data)[:500]]

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract key error-related keywords from error text."""
        keywords = []
        for pattern in [
            r'(ImportError|ModuleNotFoundError|TypeError|ValueError|RuntimeError)',
            r'(CUDA|GPU|memory|timeout)',
            r'(version|compatibility|deprecated)',
        ]:
            keywords.extend(re.findall(pattern, text, re.IGNORECASE))
        keywords.extend(re.findall(r'(\w+Error|\w+Exception)', text))
        return list(set(keywords[:10]))

    def _mock_retrieve(
        self,
        error_text: str,
        db: Session,
        dependency_names: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Return mock documentation when embeddings unavailable."""
        deps = db.query(Dependency).limit(top_k).all()
        return [
            {
                "dependency": dep.name,
                "content": f"Documentation for {dep.display_name}: {dep.description or 'Python library'}",
                "relevance_score": 0.5,
                "source": dep.documentation_url or "",
            }
            for dep in deps
        ]


class FixGenerator:
    """Generates fix suggestions using LLM."""

    def __init__(self):
        self.ollama_url = os.environ.get("LLM_OLLAMA_HOST", "http://localhost:11434")
        self.model = os.environ.get("LLM_OLLAMA_MODEL", "qwen3:8b")
        self.is_available = self._check_availability()

    def _check_availability(self) -> bool:
        """Check if Ollama is available."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False

    async def generate_fix_async(
        self,
        error_log: str,
        relevant_docs: List[Dict[str, Any]],
        dependencies: List[str]
    ) -> Dict[str, Any]:
        """Async wrapper — runs blocking Ollama HTTP call in a thread."""
        return await asyncio.to_thread(
            self.generate_fix, error_log, relevant_docs, dependencies
        )

    def generate_fix(
        self,
        error_log: str,
        relevant_docs: List[Dict[str, Any]],
        dependencies: List[str]
    ) -> Dict[str, Any]:
        """Generate a fix suggestion for the error."""
        
        if not self.is_available:
            return self._mock_fix(error_log, dependencies)

        try:
            # Build context from retrieved docs
            context = self._build_context(error_log, relevant_docs, dependencies)
            
            # Create prompt
            prompt = self._create_prompt(error_log, context, dependencies)
            
            # Call Ollama
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.3,
                },
                timeout=180
            )
            
            if response.status_code == 200:
                result = response.json()
                return self._parse_response(result["response"])
            else:
                logger.error(f"Ollama error: {response.status_code}")
                return self._mock_fix(error_log, dependencies)
                
        except Exception as e:
            logger.error(f"Error generating fix: {e}")
            return self._mock_fix(error_log, dependencies)

    def _build_context(
        self, 
        error_log: str, 
        relevant_docs: List[Dict[str, Any]], 
        dependencies: List[str]
    ) -> str:
        """Build context string from retrieved documents."""
        if not relevant_docs:
            return "No relevant documentation found in the vector store."

        context = "RELEVANT DOCUMENTATION EXCERPTS (from embedded dependency docs):\n\n"
        for i, doc in enumerate(relevant_docs[:5], 1):
            score = doc.get('relevance_score', 0)
            content = doc.get('content', '').strip()
            context += f"--- Doc {i} [{doc['dependency']}] (similarity: {score:.2f}) ---\n"
            context += f"{content[:600]}\n\n"
        
        return context

    def _create_prompt(
        self, 
        error_log: str, 
        context: str, 
        dependencies: List[str]
    ) -> str:
        """Create LLM prompt for fix generation."""
        deps_str = ', '.join(dependencies) if dependencies else 'not specified'
        prompt = f"""You are a senior Python CI/CD engineer with deep expertise in dependency management and automated pipelines. Analyze the error log below using the retrieved documentation excerpts as your primary knowledge source.

ERROR LOG:
{error_log[:1500]}

DEPENDENCIES IN USE: {deps_str}

{context}

Using the documentation excerpts above as evidence, provide a thorough analysis with these exact sections:

1. ROOT CAUSE: Explain in detail what caused the error. Reference specific version mismatches, missing packages, or configuration issues found in the documentation context.

2. SOLUTION: Step-by-step instructions to fix the error. Be specific — include exact package names, version numbers, configuration keys, or API calls that the documentation mentions.

3. CODE FIX: Provide complete, copy-paste-ready code changes. Include updated requirements.txt entries, configuration snippets, or code patches as relevant. Use fenced code blocks.

4. PREVENTION: Explain best practices from the documentation to prevent this class of error in future. Include dependency pinning strategies, CI checks, or testing steps.

5. CICD FIX: Provide a ready-to-apply CI/CD pipeline patch. Include: (a) the specific pipeline yaml change (GitHub Actions, GitLab CI, or generic shell steps) to install/fix the dependency, (b) a suggested commit message, and (c) a pull request description that explains the fix for reviewers.

Be thorough. Each section should be at least 3-5 sentences and reference the documentation where possible."""
        return prompt

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response into structured format, handling markdown and plain headers."""

        result = {
            "root_cause": "",
            "solution": "",
            "code_fix": "",
            "prevention": "",
            "cicd_fix": "",
            "full_response": response_text,
        }

        # Match both: "### 1. ROOT CAUSE" and "1. ROOT CAUSE:" style headers
        sections = re.split(
            r'(?:#{1,3}\s*)?\d+\.\s+(ROOT CAUSE|SOLUTION|CODE FIX|PREVENTION|CICD FIX)\s*:?',
            response_text,
            flags=re.IGNORECASE,
        )

        if len(sections) > 1:
            for i in range(1, len(sections), 2):
                if i + 1 < len(sections):
                    section_name = sections[i].lower()
                    section_content = sections[i + 1].strip()

                    if "root cause" in section_name:
                        result["root_cause"] = section_content[:1000]
                    elif "solution" in section_name:
                        result["solution"] = section_content[:1000]
                    elif "code" in section_name:
                        result["code_fix"] = section_content[:2000]
                    elif "prevention" in section_name:
                        result["prevention"] = section_content[:1000]
                    elif "cicd" in section_name:
                        result["cicd_fix"] = section_content[:2000]
        
        return result

    def _mock_fix(self, error_log: str, dependencies: List[str]) -> Dict[str, Any]:
        """Return mock fix when LLM unavailable."""
        return {
            "root_cause": "Analyzing error pattern from log file...",
            "solution": f"Review documentation for {', '.join(dependencies[:2])} regarding compatibility and version management.",
            "code_fix": "# Update your requirements.txt or pyproject.toml with compatible versions\n# pip install --upgrade [package-name]",
            "prevention": "Use dependency pinning and automated CI/CD testing to catch issues early.",
            "cicd_fix": "# Add to your CI pipeline:\n# - run: pip install -r requirements.txt --upgrade\n# Commit message: fix: update dependencies for compatibility\n# PR description: Updates dependency versions to resolve CI failures.",
            "full_response": "Mock response - Ollama not available",
        }


class RAGASEvaluator:
    """Evaluates RAG response quality using RAGAS-inspired metrics via a single Ollama call."""

    def __init__(self):
        self.ollama_url = os.environ.get("LLM_OLLAMA_HOST", "http://localhost:11434")
        self.model = os.environ.get("LLM_OLLAMA_MODEL", "qwen3:8b")

    async def evaluate_async(
        self,
        question: str,
        answer: str,
        contexts: List[str],
    ) -> Optional[Dict[str, float]]:
        """Async wrapper — runs blocking Ollama call in a thread."""
        return await asyncio.to_thread(self.evaluate, question, answer, contexts)

    def evaluate(
        self,
        question: str,
        answer: str,
        contexts: List[str],
    ) -> Optional[Dict[str, float]]:
        """Compute Faithfulness, Answer Relevance, Context Precision, Context Recall scores.

        Returns dict with float scores 0.0–1.0, or None if Ollama unavailable.
        """
        if not answer or not contexts:
            return None

        ctx_block = "\n".join(
            f"[Context {i + 1}]: {c[:300]}" for i, c in enumerate(contexts[:5])
        )
        prompt = (
            "You are an expert RAG evaluator. Score the following RAG output on 4 metrics.\n"
            "Return ONLY a valid JSON object — no extra text.\n\n"
            f"QUESTION (error log):\n{question[:600]}\n\n"
            f"RETRIEVED CONTEXTS:\n{ctx_block}\n\n"
            f"GENERATED ANSWER:\n{answer[:800]}\n\n"
            "Score each metric from 0.0 (poor) to 1.0 (perfect):\n"
            "- faithfulness: Are all claims in the answer supported by the retrieved contexts?\n"
            "- answer_relevance: Does the answer directly address the question / error?\n"
            "- context_precision: Are the retrieved contexts actually relevant to this error?\n"
            "- context_recall: Do the retrieved contexts cover all key information needed to explain this error?\n\n"
            'Return ONLY JSON, e.g.: {"faithfulness": 0.85, "answer_relevance": 0.90, "context_precision": 0.75, "context_recall": 0.80}'
        )
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False, "format": "json"},
                timeout=90,
            )
            raw = response.json().get("response", "{}")
            scores = json.loads(raw)
            keys = ("faithfulness", "answer_relevance", "context_precision", "context_recall")
            return {k: round(max(0.0, min(1.0, float(scores.get(k, 0.0)))), 2) for k in keys}
        except Exception as e:
            logger.warning(f"RAGAS evaluation failed: {e}")
            return None


class PipelineNotReadyError(Exception):
    """Raised when the RAG pipeline prerequisites are not met."""
    pass


class RAGEngine:
    """Main RAG orchestration engine."""

    def __init__(self, db: Session):
        self.db = db
        self.retriever = DocumentRetriever()
        self.fix_generator = FixGenerator()
        self.evaluator = RAGASEvaluator()

    async def check_pipeline_ready(self) -> None:
        """Verify all pipeline components are ready before analysis.

        Checks (in order):
        1. pgvector DB is connected and table exists
        2. At least one document chunk has been embedded
        3. Ollama embedding service is reachable

        Raises PipelineNotReadyError with a descriptive message if any check fails.
        """
        pg = self.retriever.pg_storage

        # 1. pgvector connection
        if not pg._ready:
            raise PipelineNotReadyError(
                "pgvector is not connected. Check that PostgreSQL is running and "
                "VECTORDB_POSTGRES_URL is configured correctly."
            )

        # 2. Embeddings exist (run blocking count in thread)
        chunk_count = await asyncio.to_thread(pg.count_all_chunks)
        if chunk_count == 0:
            raise PipelineNotReadyError(
                "No document embeddings found in pgvector. "
                "Please complete the Embedding step in the setup wizard "
                "(/setup/embedding) before analysing logs."
            )

        # 3. Ollama embedding model reachable
        if not self.retriever.is_available:
            raise PipelineNotReadyError(
                "Ollama embedding service is unreachable. "
                "Ensure Ollama is running and the embedding model (e.g. nomic-embed-text) "
                "is pulled before analysing logs."
            )

        logger.info(f"✓ Pipeline ready — {chunk_count} chunks indexed in pgvector")

    async def analyze_error_and_generate_fix(
        self,
        log_id: str,
        user_id: str,
        selected_dependencies: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Async: Analyze error log and generate fix suggestions."""

        # DB queries are fast; run in thread to be safe in async context
        log = await asyncio.to_thread(
            lambda: self.db.query(Log).filter(
                Log.id == log_id, Log.user_id == user_id
            ).first()
        )

        if not log:
            raise ValueError(f"Log {log_id} not found")

        # Guard: ensure embedding pipeline is ready before attempting retrieval
        await self.check_pipeline_ready()

        # Retrieve docs (embedding call — blocking network I/O)
        relevant_docs = await self.retriever.retrieve_relevant_docs_async(
            error_text=log.error_summary.get("sample_errors", [{}])[0].get("content", log.content[:500]),
            db=self.db,
            dependency_names=selected_dependencies,
            top_k=5
        )

        # Generate fix (LLM call — blocking network I/O, up to 3 min)
        dependencies = selected_dependencies or []
        fix = await self.fix_generator.generate_fix_async(
            error_log=log.content[:2000],
            relevant_docs=relevant_docs,
            dependencies=dependencies,
        )

        # RAGAS evaluation runs after fix is ready (needs the generated answer)
        contexts = [d.get("content", "") for d in relevant_docs]
        ragas_scores = await self.evaluator.evaluate_async(
            question=log.content[:800],
            answer=fix.get("full_response", ""),
            contexts=contexts,
        )

        # Store query result
        query = Query(
            id=str(uuid.uuid4()),
            user_id=user_id,
            log_id=log_id,
            query_text=log.content[:500],
            query_intent="fix",
            selected_dependencies=dependencies,
            retrieved_docs=relevant_docs,
            generated_response=fix["full_response"],
            suggested_fixes=[fix],
        )
        await asyncio.to_thread(lambda: (self.db.add(query), self.db.commit()))

        logger.info(f"✓ Generated fix for log {log_id}")

        return {
            "query_id": query.id,
            "log_id": log_id,
            "error_summary": log.error_summary,
            "retrieved_docs_count": len(relevant_docs),
            "fix": fix,
            "dependencies_analyzed": dependencies,
            "ragas_scores": ragas_scores,
        }
