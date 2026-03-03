"""PGVector adapter for PostgreSQL vector storage."""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from .base import VectorDBAdapter

logger = logging.getLogger(__name__)


class PGVectorAdapter(VectorDBAdapter):
    """PostgreSQL with pgvector extension adapter.

    Stores embeddings in PostgreSQL with pgvector extension.
    Collections are stored in separate tables.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize PGVector adapter.

        Args:
            config: Must contain:
                - database_url: PostgreSQL connection string
                - pool_size: Connection pool size (default: 5)
        """
        super().__init__(config)
        self.database_url = config.get("database_url")
        self.pool_size = config.get("pool_size", 5)
        self.engine: Optional[Any] = None
        self.session: Optional[AsyncSession] = None

    async def connect(self) -> bool:
        """Connect to PostgreSQL with pgvector.

        Returns:
            True if connection successful
        """
        try:
            from sqlalchemy.ext.asyncio import create_async_engine

            self.engine = create_async_engine(
                self.database_url,
                pool_size=self.pool_size,
                max_overflow=10,
                echo=False,
            )

            # Test connection
            async with self.engine.begin() as conn:
                # Enable pgvector extension
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                await conn.commit()

            self.is_connected = True
            logger.info(f"Connected to PostgreSQL with pgvector")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            return False

    async def disconnect(self) -> bool:
        """Disconnect from PostgreSQL.

        Returns:
            True if disconnection successful
        """
        try:
            if self.engine:
                await self.engine.dispose()
                self.is_connected = False
                logger.info("Disconnected from PostgreSQL")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
            return False

    async def create_collection(
        self,
        collection_name: str,
        vector_size: int = 384,
        metadata_schema: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Create a collection (table with vector column).

        Args:
            collection_name: Name of collection
            vector_size: Dimension of vectors
            metadata_schema: Schema for metadata columns

        Returns:
            True if successful
        """
        if not self.engine or not self.is_connected:
            logger.error("Not connected to PostgreSQL")
            return False

        try:
            async with self.engine.begin() as conn:
                # Create table with vector column
                create_sql = f"""
                CREATE TABLE IF NOT EXISTS {collection_name} (
                    id SERIAL PRIMARY KEY,
                    text TEXT NOT NULL,
                    embedding vector({vector_size}) NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
                await conn.execute(text(create_sql))

                # Create index for vector similarity search
                index_sql = f"""
                CREATE INDEX IF NOT EXISTS {collection_name}_embedding_idx
                ON {collection_name}
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
                """
                await conn.execute(text(index_sql))

                await conn.commit()

            logger.info(f"Created collection: {collection_name}")
            return True

        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            return False

    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection (drop table).

        Args:
            collection_name: Name of collection

        Returns:
            True if successful
        """
        if not self.engine or not self.is_connected:
            logger.error("Not connected to PostgreSQL")
            return False

        try:
            async with self.engine.begin() as conn:
                drop_sql = f"DROP TABLE IF EXISTS {collection_name} CASCADE"
                await conn.execute(text(drop_sql))
                await conn.commit()

            logger.info(f"Deleted collection: {collection_name}")
            return True

        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
            return False

    async def store(
        self,
        text: str,
        embedding: List[float],
        metadata: Dict[str, Any],
        collection: str = "documents",
    ) -> bool:
        """Store document embedding.

        Args:
            text: Original text
            embedding: Vector embedding
            metadata: Associated metadata
            collection: Collection name

        Returns:
            True if successful
        """
        if not self.engine or not self.is_connected:
            logger.error("Not connected to PostgreSQL")
            return False

        try:
            import json

            async with self.engine.begin() as conn:
                # Convert embedding to string format for pgvector
                embedding_str = f"[{','.join(map(str, embedding))}]"
                metadata_json = json.dumps(metadata)

                insert_sql = f"""
                INSERT INTO {collection} (text, embedding, metadata)
                VALUES (:text, :embedding, :metadata)
                """

                await conn.execute(
                    text(insert_sql),
                    {
                        "text": text,
                        "embedding": embedding_str,
                        "metadata": metadata_json,
                    },
                )
                await conn.commit()

            return True

        except Exception as e:
            logger.error(f"Error storing embedding: {e}")
            return False

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
            threshold: Similarity threshold (cosine distance 0-1)

        Returns:
            List of results with text, metadata, and score
        """
        if not self.engine or not self.is_connected:
            logger.error("Not connected to PostgreSQL")
            return []

        try:
            embedding_str = f"[{','.join(map(str, embedding))}]"

            search_sql = f"""
            SELECT
                id,
                text,
                metadata,
                1 - (embedding <=> :embedding::vector) as similarity
            FROM {collection}
            WHERE 1 - (embedding <=> :embedding::vector) > COALESCE(:threshold, 0)
            ORDER BY embedding <=> :embedding::vector
            LIMIT :top_k
            """

            async with self.engine.connect() as conn:
                result = await conn.execute(
                    text(search_sql),
                    {
                        "embedding": embedding_str,
                        "threshold": threshold or 0,
                        "top_k": top_k,
                    },
                )

                rows = await result.fetchall()

            import json

            results = [
                {
                    "id": row[0],
                    "text": row[1],
                    "metadata": json.loads(row[2]) if row[2] else {},
                    "score": float(row[3]),
                }
                for row in rows
            ]

            return results

        except Exception as e:
            logger.error(f"Error searching: {e}")
            return []

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
        if not self.engine or not self.is_connected:
            logger.error("Not connected to PostgreSQL")
            return 0

        try:
            import json

            # Build WHERE clause for metadata
            conditions = []
            for key, value in metadata_filter.items():
                conditions.append(f"metadata->'{key}' = '{json.dumps(value)}'")

            where_clause = " AND ".join(conditions) if conditions else "TRUE"

            delete_sql = f"""
            DELETE FROM {collection}
            WHERE {where_clause}
            """

            async with self.engine.begin() as conn:
                result = await conn.execute(text(delete_sql))
                deleted_count = result.rowcount
                await conn.commit()

            logger.info(f"Deleted {deleted_count} documents from {collection}")
            return deleted_count

        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            return 0

    async def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get collection statistics.

        Args:
            collection_name: Name of collection

        Returns:
            Info dict with count, size, etc.
        """
        if not self.engine or not self.is_connected:
            logger.error("Not connected to PostgreSQL")
            return {}

        try:
            async with self.engine.connect() as conn:
                # Row count
                count_result = await conn.execute(
                    text(f"SELECT COUNT(*) FROM {collection_name}")
                )
                count = await count_result.scalar()

                # Table size
                size_result = await conn.execute(
                    text(
                        f"""
                        SELECT pg_total_relation_size('{collection_name}'::regclass)
                        """
                    )
                )
                size_bytes = await size_result.scalar()

            return {
                "collection": collection_name,
                "row_count": count,
                "size_bytes": size_bytes,
                "avg_row_size": size_bytes / count if count > 0 else 0,
            }

        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {}

    async def health_check(self) -> bool:
        """Check if database is healthy.

        Returns:
            True if healthy
        """
        try:
            if not self.engine:
                return False

            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                return True

        except Exception as e:
            logger.debug(f"PGVector health check failed: {e}")
            return False
