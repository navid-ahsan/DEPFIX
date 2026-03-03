"""Ollama embedding model adapter implementation."""

import httpx
import asyncio
import logging
from typing import Any, Dict, List, Optional
from .base import EmbeddingAdapter

logger = logging.getLogger(__name__)


class OllamaEmbeddingAdapter(EmbeddingAdapter):
    """Ollama embedding adapter for local embedding models.

    Uses Ollama API for generating embeddings with local models.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize Ollama embedding adapter.

        Args:
            config: Must contain:
                - host: Ollama server host (default: http://localhost:11434)
                - model: Embedding model name (e.g., 'nomic-embed-text', 'mxbai-embed-large')
                - timeout: Request timeout in seconds (default: 60)
        """
        super().__init__(config)
        self.host = config.get("host", "http://localhost:11434")
        self.timeout = config.get("timeout", 60)
        self.client: Optional[httpx.AsyncClient] = None
        self._embedding_dim: Optional[int] = None

    async def connect(self) -> bool:
        """Connect to Ollama service.

        Returns:
            True if connection successful
        """
        try:
            self.client = httpx.AsyncClient(timeout=self.timeout)
            health = await self.health_check()

            if health:
                # Get embedding dimension
                self._embedding_dim = await self.get_embedding_dimension()
                self.is_connected = True
                logger.info(
                    f"Connected to Ollama embeddings at {self.host} "
                    f"(dim: {self._embedding_dim})"
                )
                return True
            else:
                logger.error(f"Ollama health check failed at {self.host}")
                return False

        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            return False

    async def disconnect(self) -> bool:
        """Disconnect from Ollama service.

        Returns:
            True if disconnection successful
        """
        try:
            if self.client:
                await self.client.aclose()
                self.is_connected = False
                logger.info("Disconnected from Ollama embeddings")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from Ollama: {e}")
            return False

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of text strings

        Returns:
            List of embedding vectors
        """
        if not self.is_connected or not self.client:
            logger.error("Not connected to Ollama")
            return []

        embeddings = []

        try:
            # Ollama API generates one embedding at a time
            for text in texts:
                embedding = await self.embed_single(text)
                embeddings.append(embedding)

            return embeddings

        except Exception as e:
            logger.error(f"Error embedding texts: {e}")
            return []

    async def embed_single(self, text: str) -> List[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        if not self.is_connected or not self.client:
            logger.error("Not connected to Ollama")
            return []

        try:
            response = await self.client.post(
                f"{self.host}/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text,
                },
            )

            if response.status_code != 200:
                logger.error(f"Ollama embedding error: {response.status_code}")
                return []

            import json
            data = json.loads(response.text)
            embedding = data.get("embedding", [])

            return embedding

        except Exception as e:
            logger.error(f"Error embedding text: {e}")
            return []

    async def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings from this model.

        Returns:
            Vector dimension size
        """
        if not self.client:
            return 0

        try:
            # Test with a dummy text
            response = await self.client.post(
                f"{self.host}/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": "test",
                },
            )

            if response.status_code == 200:
                import json
                data = json.loads(response.text)
                embedding = data.get("embedding", [])
                return len(embedding)

            return 0

        except Exception as e:
            logger.error(f"Error getting embedding dimension: {e}")
            return 0

    async def list_models(self) -> List[str]:
        """List available embedding models in Ollama.

        Returns:
            List of model names
        """
        if not self.is_connected or not self.client:
            return []

        try:
            response = await self.client.get(f"{self.host}/api/tags")

            if response.status_code == 200:
                import json
                data = json.loads(response.text)
                models = [m["name"] for m in data.get("models", [])]
                return models

            return []

        except Exception as e:
            logger.error(f"Error listing Ollama models: {e}")
            return []

    async def health_check(self) -> bool:
        """Check if Ollama service is running.

        Returns:
            True if healthy
        """
        try:
            if not self.client:
                return False

            response = await self.client.get(f"{self.host}/api/tags", timeout=5)
            return response.status_code == 200

        except Exception as e:
            logger.debug(f"Ollama health check failed: {e}")
            return False
