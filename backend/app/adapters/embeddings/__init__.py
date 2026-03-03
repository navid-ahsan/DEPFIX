"""Embedding model adapters."""

from .base import EmbeddingAdapter
from .ollama import OllamaEmbeddingAdapter

__all__ = [
    "EmbeddingAdapter",
    "OllamaEmbeddingAdapter",
]
