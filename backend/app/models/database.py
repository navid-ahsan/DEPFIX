"""SQLAlchemy database models."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid

Base = declarative_base()


class User(Base):
    """User model."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Optional for OAuth
    is_active = Column(Boolean, default=True, index=True)
    is_admin = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    logs = relationship("Log", back_populates="user", cascade="all, delete-orphan")
    queries = relationship("Query", back_populates="user", cascade="all, delete-orphan")
    agent_runs = relationship("AgentRun", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class Log(Base):
    """Error log file model."""

    __tablename__ = "logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)  # Raw log content
    file_format = Column(String(50), default="txt")  # txt, json, log, etc.
    file_size_bytes = Column(Integer)

    # Processing metadata
    is_processed = Column(Boolean, default=False, index=True)
    error_count = Column(Integer, default=0)
    primary_error_type = Column(String(255), nullable=True)
    primary_error_category = Column(String(255), nullable=True)

    # Extracted error info (JSON)
    extracted_errors = Column(JSON, nullable=True)
    error_summary = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="logs")
    queries = relationship("Query", back_populates="log")

    def __repr__(self) -> str:
        return f"<Log {self.filename}>"


class Dependency(Base):
    """Known Python dependency/package model."""

    __tablename__ = "dependencies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(255))  # e.g., "PyTorch" for "torch"
    description = Column(Text, nullable=True)

    # Metadata
    homepage = Column(String(500))
    documentation_url = Column(String(500))
    pypi_url = Column(String(500))
    repository_url = Column(String(500))

    # Version tracking
    latest_version = Column(String(50))
    last_version_check = Column(DateTime)

    # Cached documentation
    docs_cache = Column(JSON, nullable=True)  # Cached doc snippets
    docs_cached_at = Column(DateTime)

    # Category for filtering
    category = Column(String(50))  # ml, web, data, crypto, etc.
    is_active = Column(Boolean, default=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    queries = relationship("Query", secondary="query_dependencies", back_populates="dependencies")

    def __repr__(self) -> str:
        return f"<Dependency {self.name}>"


class Query(Base):
    """RAG query and result model."""

    __tablename__ = "queries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    log_id = Column(String(36), ForeignKey("logs.id"), nullable=True)

    # Query content
    query_text = Column(Text, nullable=False)
    query_intent = Column(String(50))  # guidance, fix, analysis
    query_intent_category = Column(String(50))  # dependency, incompatibility, runtime, etc.

    # Selected dependencies
    selected_dependencies = Column(JSON, nullable=True)  # List of dependency names

    # RAG Processing
    retrieved_docs = Column(JSON, nullable=True)  # Retrieved context chunks
    retrieval_scores = Column(JSON, nullable=True)  # Relevance scores

    # LLM Result
    generated_response = Column(Text, nullable=True)
    response_quality = Column(String(50))  # good, moderate, poor
    is_response_approved = Column(Boolean, default=False)

    # Code suggestions (if applicable)
    suggested_fixes = Column(JSON, nullable=True)
    accepted_fix = Column(JSON, nullable=True)
    fix_executed = Column(Boolean, default=False)
    fix_result = Column(JSON, nullable=True)

    # Evaluation
    is_evaluated = Column(Boolean, default=False)
    evaluation_score = Column(String(50))  # 1.0-5.0 or good/fair/poor
    evaluation_feedback = Column(Text)
    evaluation_metadata = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="queries")
    log = relationship("Log", back_populates="queries")
    dependencies = relationship(
        "Dependency",
        secondary="query_dependencies",
        back_populates="queries"
    )

    def __repr__(self) -> str:
        return f"<Query {self.id[:8]}>"


class QueryDependency(Base):
    """Many-to-many relationship between queries and dependencies."""

    __tablename__ = "query_dependencies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    query_id = Column(String(36), ForeignKey("queries.id"), nullable=False, index=True)
    dependency_id = Column(String(36), ForeignKey("dependencies.id"), nullable=False, index=True)

    # Track when dependency was added to query
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<QueryDependency {self.query_id} -> {self.dependency_id}>"


class VectorStore(Base):
    """Model for tracking which embeddings have been indexed."""

    __tablename__ = "vector_stores"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dependency_id = Column(String(36), ForeignKey("dependencies.id"), nullable=False)
    collection_name = Column(String(255), nullable=False, index=True)

    # Tracking
    chunk_count = Column(Integer, default=0)
    is_indexed = Column(Boolean, default=False)
    embedding_model = Column(String(255))
    vector_db_type = Column(String(50))  # pgvector, milvus, weaviate, etc.

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<VectorStore {self.collection_name}>"


class SetupStatus(Base):
    """User setup progress tracking."""

    __tablename__ = "setup_status"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True)

    # Phase 1: Dependencies
    selected_dependencies = Column(JSON, nullable=True)  # List of dependency names
    phase1_completed = Column(Boolean, default=False)

    # Phase 2: Embeddings & Vector DB
    phase2_completed = Column(Boolean, default=False)
    embeddings_status = Column(String(50), default="pending")  # pending, in_progress, completed

    # Phase 3: GitHub/GitLab Connection
    github_gitlab_connected = Column(Boolean, default=False)
    phase3_completed = Column(Boolean, default=False)

    # Phase 4: RAG Ready
    rag_ready = Column(Boolean, default=False)

    # Error tracking
    last_error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="setup_status")

    def __repr__(self) -> str:
        return f"<SetupStatus {self.user_id[:8]}>"


class APIKey(Base):
    """API key model for external integrations."""

    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    service = Column(String(50))  # github, gitlab, openai, etc.
    key_hash = Column(String(255), nullable=False)  # Hashed key
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<APIKey {self.service}>"


class DEPFIXApiKey(Base):
    """API key for authenticating CI/CD pipelines and external callers to DEPFIX."""

    __tablename__ = "depfix_api_keys"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)          # e.g. "GitHub Actions – main repo"
    key_hash = Column(String(255), nullable=False)      # pbkdf2 hash, never stored plaintext
    is_active = Column(Boolean, default=True, index=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="depfix_api_keys")

    def __repr__(self) -> str:
        return f"<DEPFIXApiKey {self.name!r} user={self.user_id[:8]}>"


class UserConfig(Base):
    """User-editable runtime configuration (connectivity, models, prompts)."""

    __tablename__ = "user_config"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, unique=True, index=True)

    # Connectivity
    ollama_url = Column(String(500), default="http://localhost:11434")
    postgres_url = Column(String(500), default="postgresql+psycopg2://postgres:password123@localhost:5432/vector_db")

    # GitHub / GitLab integration tokens (stored in plaintext for API calls;
    # only kept in the user's own database instance — self-hosted model)
    github_token = Column(String(500), nullable=True)
    gitlab_token = Column(String(500), nullable=True)
    gitlab_url = Column(String(500), default="https://gitlab.com")

    # Selected models
    llm_model = Column(String(255), default="")
    embedding_model = Column(String(255), default="nomic-embed-text")

    # LLM parameters
    temperature = Column(String(10), default="0.2")
    max_tokens = Column(Integer, default=2048)
    system_prompt = Column(Text, nullable=True)
    preferred_quantization = Column(String(50), default="q4_K_M")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<UserConfig user={self.user_id}>"


class AgentRun(Base):
    """Persistent orchestration run metadata for replay/debug/inspection."""

    __tablename__ = "agent_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    query_text = Column(Text, nullable=False)
    intent = Column(String(50), default="guidance", index=True)
    selected_dependencies = Column(JSON, nullable=True)
    execution_plan = Column(JSON, nullable=True)  # ordered list of agent names

    status = Column(String(32), default="running", index=True)  # running/completed/failed
    run_graph = Column(JSON, nullable=True)  # structure for future DAG mode
    budget = Column(JSON, nullable=True)  # {max_seconds, max_api_calls, ...}
    metrics = Column(JSON, nullable=True)  # aggregate timings/quality metadata
    error_text = Column(Text, nullable=True)

    started_at = Column(DateTime, default=datetime.utcnow, index=True)
    ended_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="agent_runs")
    steps = relationship("AgentRunStep", back_populates="run", cascade="all, delete-orphan")


class AgentRunStep(Base):
    """Per-agent execution record for a run."""

    __tablename__ = "agent_run_steps"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String(36), ForeignKey("agent_runs.id"), nullable=False, index=True)
    step_order = Column(Integer, nullable=False)
    agent_name = Column(String(120), nullable=False, index=True)

    status = Column(String(32), default="pending", index=True)  # pending/running/completed/failed/skipped
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    retry_count = Column(Integer, default=0)

    input_snapshot = Column(JSON, nullable=True)
    output_summary = Column(JSON, nullable=True)
    tool_calls = Column(JSON, nullable=True)  # reserved for future tool-level tracing
    artifacts = Column(JSON, nullable=True)  # e.g. generated patches, test logs
    error_text = Column(Text, nullable=True)

    run = relationship("AgentRun", back_populates="steps")
