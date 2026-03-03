"""Abstract base class for vector database adapters."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class VectorDBAdapter(ABC):
    """Abstract base class for vector database adapters.

    Implementations: PGVector, Milvus, Weaviate, Pinecone, etc.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize adapter with configuration.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.is_connected = False

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to vector database.

        Returns:
            True if connection successful
        """
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from vector database.

        Returns:
            True if disconnection successful
        """
        pass

    @abstractmethod
    async def create_collection(
        self,
        collection_name: str,
        vector_size: int = 384,
        metadata_schema: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Create a collection/index.

        Args:
            collection_name: Name of collection
            vector_size: Dimension of vectors
            metadata_schema: Schema for metadata fields

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection/index.

        Args:
            collection_name: Name of collection

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def store(
        self,
        text: str,
        embedding: List[float],
        metadata: Dict[str, Any],
        collection: str = "documents",
    ) -> bool:
        """Store document embedding in vector DB.

        Args:
            text: Original text
            embedding: Vector embedding
            metadata: Associated metadata
            collection: Collection name

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def search(
        self,
        embedding: List[float],
        collection: str = "documents",
        top_k: int = 5,
        threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar embeddings.

        Args:
            embedding: Query embedding
            collection: Collection to search
            top_k: Number of results
            threshold: Similarity threshold

        Returns:
            List of results with text, metadata, and score
        """
        pass

    @abstractmethod
    async def delete(
        self,
        metadata_filter: Dict[str, Any],
        collection: str = "documents",
    ) -> int:
        """Delete documents matching metadata.

        Args:
            metadata_filter: Metadata filter criteria
            collection: Collection to delete from

        Returns:
            Number of documents deleted
        """
        pass

    @abstractmethod
    async def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get collection statistics.

        Args:
            collection_name: Name of collection

        Returns:
            Info dict with count, size, etc.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if database is healthy.

        Returns:
            True if healthy
        """
        pass
