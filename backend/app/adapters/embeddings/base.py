"""Abstract base class for embedding model adapters."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class EmbeddingAdapter(ABC):
    """Abstract base class for embedding model adapters.

    Implementations: Ollama, OpenAI, Hugging Face, Sentence Transformers, etc.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize adapter with configuration.

        Args:
            config: Configuration dictionary (host, model, pool_size, etc.)
        """
        self.config = config
        self.is_connected = False
        self.model = config.get("model", "default-embedding-model")
        self.embedding_dim: Optional[int] = None

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to embedding service.

        Returns:
            True if connection successful
        """
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from embedding service.

        Returns:
            True if disconnection successful
        """
        pass

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (one per text)
        """
        pass

    @abstractmethod
    async def embed_single(self, text: str) -> List[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        pass

    @abstractmethod
    async def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings.

        Returns:
            Vector dimension size
        """
        pass

    @abstractmethod
    async def list_models(self) -> List[str]:
        """List available embedding models.

        Returns:
            List of model names
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if embedding service is healthy.

        Returns:
            True if healthy
        """
        pass
