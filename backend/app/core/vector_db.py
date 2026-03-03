"""Vector database utilities for RAG pipeline.

Provides abstraction over different vector DB backends (pgvector, ChromaDB, etc.).
Currently focused on pgvector with PostgreSQL.
"""

from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores.pgvector import PGVector
import logging

logger = logging.getLogger(__name__)


class VectorDBManager:
    """Manages vector database operations for the RAG pipeline."""

    def __init__(
        self,
        db_type: str = "pgvector",
        connection_string: str = "postgresql+psycopg2://postgres:root@localhost:5432/vector_db",
        collection_name: str = "Error_handling",
        embedding_model: str = "nomic-embed-text",
        embedding_host: str = "http://localhost:11434",
        chunk_size: int = 1024,
        chunk_overlap: int = 300,
    ):
        """Initialize vector DB manager.

        Args:
            db_type: Type of vector DB (pgvector, chromadb, milvus, etc.)
            connection_string: Database connection string
            collection_name: Name of the collection/table
            embedding_model: Name of the embedding model
            embedding_host: Base URL of Ollama or embedding service
            chunk_size: Document chunk size for splitting
            chunk_overlap: Overlap between chunks
        """
        if db_type != "pgvector":
            raise NotImplementedError(f"DB type '{db_type}' not yet supported")

        self.db_type = db_type
        self.connection_string = connection_string
        self.collection_name = collection_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedding_model = embedding_model
        self.embedding_host = embedding_host

        # Initialize embeddings
        try:
            self.embeddings = OllamaEmbeddings(
                model=embedding_model,
                base_url=embedding_host,
            )
            logger.info(f"Initialized embeddings: {embedding_model}")
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
            self.embeddings = None

        self.vector_store = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )

    def connect(self) -> bool:
        """Establish connection to vector database.

        Returns:
            True if successful, False otherwise.
        """
        if not self.embeddings:
            logger.error("Embeddings not initialized")
            return False

        try:
            self.vector_store = PGVector(
                embedding_function=self.embeddings,
                collection_name=self.collection_name,
                connection_string=self.connection_string,
                use_jsonb=True,
            )
            logger.info(f"Connected to {self.db_type} collection '{self.collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to vector DB: {e}")
            return False

    def index_documents(self, documents: List[Document]) -> int:
        """Add documents to the vector store.

        Args:
            documents: List of LangChain Document objects

        Returns:
            Number of documents indexed
        """
        if not self.vector_store:
            logger.warning("Vector store not connected")
            return 0

        try:
            # Split documents into chunks
            chunks = self.text_splitter.split_documents(documents)
            logger.info(f"Split {len(documents)} docs into {len(chunks)} chunks")

            # Add to store
            ids = self.vector_store.add_documents(chunks, ids=None)
            logger.info(f"Indexed {len(ids)} chunk(s)")
            return len(ids)
        except Exception as e:
            logger.error(f"Failed to index documents: {e}")
            return 0

    def search(self, query: str, k: int = 5) -> List[tuple]:
        """Search for relevant documents.

        Args:
            query: Search query string
            k: Number of results to return

        Returns:
            List of (Document, similarity_score) tuples
        """
        if not self.vector_store:
            logger.warning("Vector store not connected")
            return []

        try:
            results = self.vector_store.similarity_search_with_score(query, k=k)
            logger.info(f"Found {len(results)} results for query")
            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def clear(self) -> bool:
        """Clear all documents from the collection.

        Returns:
            True if successful
        """
        if not self.vector_store:
            logger.warning("Vector store not connected")
            return False

        try:
            # For pgvector, we drop and recreate the collection
            from sqlalchemy import text, create_engine
            engine = create_engine(self.connection_string)
            with engine.connect() as conn:
                conn.execute(text(f"DROP TABLE IF EXISTS langchain_pg_collection CASCADE"))
                conn.execute(text(f"DROP TABLE IF EXISTS langchain_pg_embedding CASCADE"))
                conn.commit()
            logger.info(f"Cleared collection '{self.collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            return False
