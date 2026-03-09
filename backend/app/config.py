"""
Configuration management for RAG Framework using Pydantic Settings.
Supports environment variables, .env files, and TOML configurations.
"""

from typing import Optional
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import os


class LLMSettings(BaseSettings):
    """LLM Configuration"""
    type: str = Field(default="ollama", description="LLM provider: ollama, openai, etc.")
    ollama_host: str = Field(default="http://ollama:11434", description="Ollama API endpoint")
    ollama_model: str = Field(default="mistral:7b", description="Default Ollama model")
    temperature: float = Field(default=0.2, ge=0.0, le=1.0, description="LLM temperature")
    max_tokens: int = Field(default=2048, description="Max tokens in response")
    timeout: int = Field(default=120, description="Timeout in seconds")

    class Config:
        env_prefix = "LLM_"


class EmbeddingSettings(BaseSettings):
    """Embedding Model Configuration"""
    type: str = Field(default="ollama", description="Embedding provider")
    ollama_host: str = Field(default="http://ollama:11434", description="Ollama API endpoint")
    model: str = Field(default="nomic-embed-text", description="Embedding model")
    dimension: int = Field(default=768, description="Embedding dimension")

    class Config:
        env_prefix = "EMBEDDING_"


class VectorDBSettings(BaseSettings):
    """Vector Database Configuration"""
    type: str = Field(default="pgvector", description="Vector DB: pgvector, milvus, weaviate")

    # PGVector Settings
    postgres_url: str = Field(
        default="postgresql+psycopg2://postgres:root@pgvector:5432/vector_db",
        description="PostgreSQL connection string"
    )
    collection_name: str = Field(default="Error_handling", description="Vector collection name")

    # Chunking Settings
    chunk_size: int = Field(default=1024, description="Document chunk size")
    chunk_overlap: int = Field(default=300, description="Chunk overlap")

    # Search Settings
    search_k: int = Field(default=5, description="Number of results to retrieve")
    distance_threshold: float = Field(default=0.3, description="Min similarity score")

    class Config:
        env_prefix = "VECTORDB_"


class GitHubSettings(BaseSettings):
    """GitHub Integration Configuration"""
    enabled: bool = Field(default=False, description="Enable GitHub integration")
    client_id: Optional[str] = Field(default=None, description="GitHub OAuth2 Client ID")
    client_secret: Optional[str] = Field(default=None, description="GitHub OAuth2 Client Secret")
    redirect_uri: str = Field(default="http://localhost:8000/api/integrations/github/callback")

    class Config:
        env_prefix = "GITHUB_"


class GitLabSettings(BaseSettings):
    """GitLab Integration Configuration"""
    enabled: bool = Field(default=False, description="Enable GitLab integration")
    client_id: Optional[str] = Field(default=None, description="GitLab OAuth2 Client ID")
    client_secret: Optional[str] = Field(default=None, description="GitLab OAuth2 Client Secret")
    redirect_uri: str = Field(default="http://localhost:8000/api/integrations/gitlab/callback")

    class Config:
        env_prefix = "GITLAB_"


class Settings(BaseSettings):
    """Main Application Settings"""

    # App Metadata
    app_name: str = Field(default="RAG Framework", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    environment: str = Field(default="development", description="Environment: development, staging, production")
    debug: bool = Field(default=False, description="Enable debug mode")

    # API Settings
    api_title: str = Field(default="RAG Framework API", description="API title")
    api_version: str = Field(default="v1", description="API version")
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    cors_origins: list = Field(default=["http://localhost:3000", "http://localhost:5173"], description="CORS origins")

    # Security
    secret_key: str = Field(default="your-secret-key-change-in-production", description="Secret key for JWT")
    access_token_expire_minutes: int = Field(default=30, description="JWT expiry in minutes")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[str] = Field(default=None, description="Log file path")

    # Database
    database_url: str = Field(
        default="sqlite:///./rag_framework.db",
        description="SQLAlchemy database URL"
    )

    # RAG Settings
    llm: LLMSettings = Field(default_factory=LLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    vector_db: VectorDBSettings = Field(default_factory=VectorDBSettings)

    # Integrations
    github: GitHubSettings = Field(default_factory=GitHubSettings)
    gitlab: GitLabSettings = Field(default_factory=GitLabSettings)

    # Storage
    upload_dir: str = Field(default="./data/uploads", description="File upload directory")
    cache_dir: str = Field(default="./data/cache", description="Cache directory")

    # Evaluation Settings
    ragas_batch_size: int = Field(default=2, description="Batch size for RAGAS evaluation")
    ragas_timeout: int = Field(default=900, description="RAGAS evaluation timeout in seconds")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses dependency injection in FastAPI.
    """
    return Settings()


# Export settings instance
settings = get_settings()
