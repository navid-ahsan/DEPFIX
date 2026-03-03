"""LLM adapters."""

from .base import LLMAdapter
from .ollama import OllamaLLMAdapter

__all__ = [
    "LLMAdapter",
    "OllamaLLMAdapter",
]
