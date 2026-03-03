"""RAG Engine - Core RAG processing logic."""

import asyncio
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class RAGEngine:
    """Core RAG (Retrieval-Augmented Generation) engine.

    Handles:
    - Document chunking and preprocessing
    - Vector embedding and retrieval
    - LLM-based answer generation
    - Context management
    """

    def __init__(
        self,
        vector_db_adapter: Optional[Any] = None,
        llm_adapter: Optional[Any] = None,
        embedding_adapter: Optional[Any] = None,
    ):
        """Initialize RAG engine with pluggable adapters.

        Args:
            vector_db_adapter: Vector database adapter (PGVector, Milvus, etc.)
            llm_adapter: LLM adapter (Ollama, OpenAI, etc.)
            embedding_adapter: Embedding model adapter
        """
        self.vector_db = vector_db_adapter
        self.llm = llm_adapter
        self.embedding = embedding_adapter
        self.context_window: List[Dict[str, Any]] = []

    async def chunk_documents(
        self,
        documents: List[str],
        chunk_size: int = 512,
        overlap: int = 50,
    ) -> List[Dict[str, Any]]:
        """Chunk documents for embedding.

        Args:
            documents: List of document texts
            chunk_size: Characters per chunk
            overlap: Character overlap between chunks

        Returns:
            List of chunk dicts with text and metadata
        """
        chunks = []

        for doc_idx, doc in enumerate(documents):
            words = doc.split()
            current_chunk = []
            current_chars = 0

            for word in words:
                word_len = len(word) + 1  # +1 for space

                if current_chars + word_len > chunk_size and current_chunk:
                    # Save current chunk
                    chunk_text = " ".join(current_chunk)
                    chunks.append({
                        "text": chunk_text,
                        "doc_index": doc_idx,
                        "char_count": len(chunk_text),
                    })

                    # Overlap: keep last words from previous chunk
                    overlap_words = int(overlap / (len(current_chunk[-1]) + 1))
                    current_chunk = current_chunk[-overlap_words:] if overlap_words > 0 else []
                    current_chars = sum(len(w) + 1 for w in current_chunk)

                current_chunk.append(word)
                current_chars += word_len

            # Add final chunk
            if current_chunk:
                chunk_text = " ".join(current_chunk)
                chunks.append({
                    "text": chunk_text,
                    "doc_index": doc_idx,
                    "char_count": len(chunk_text),
                })

        logger.info(f"Created {len(chunks)} chunks from {len(documents)} documents")
        return chunks

    async def embed_and_store(
        self,
        chunks: List[Dict[str, Any]],
        collection_name: str = "documents",
    ) -> bool:
        """Embed chunks and store in vector database.

        Args:
            chunks: List of chunk dicts
            collection_name: Name of collection in vector DB

        Returns:
            True if successful, False otherwise
        """
        if not self.embedding or not self.vector_db:
            logger.error("Embedding or Vector DB adapter not configured")
            return False

        try:
            # Generate embeddings for each chunk
            texts = [chunk["text"] for chunk in chunks]
            embeddings = await self.embedding.embed(texts)

            # Store in vector DB with metadata
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                metadata = {
                    "doc_index": chunk["doc_index"],
                    "char_count": chunk["char_count"],
                    "chunk_index": i,
                }
                await self.vector_db.store(
                    text=chunk["text"],
                    embedding=embedding,
                    metadata=metadata,
                    collection=collection_name,
                )

            logger.info(f"Stored {len(chunks)} embeddings in vector DB")
            return True

        except Exception as e:
            logger.error(f"Error embedding and storing chunks: {e}")
            return False

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        collection_name: str = "documents",
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant documents for query.

        Args:
            query: Query text
            top_k: Number of results to return
            collection_name: Collection to search

        Returns:
            List of relevant chunks with scores
        """
        if not self.embedding or not self.vector_db:
            logger.error("Embedding or Vector DB adapter not configured")
            return []

        try:
            # Embed query
            query_embedding = await self.embedding.embed([query])
            query_embedding = query_embedding[0]

            # Search vector DB
            results = await self.vector_db.search(
                embedding=query_embedding,
                top_k=top_k,
                collection=collection_name,
            )

            logger.info(f"Retrieved {len(results)} results for query")
            return results

        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return []

    async def generate(
        self,
        query: str,
        context: List[str],
        system_prompt: Optional[str] = None,
    ) -> str:
        """Generate answer using LLM with retrieved context.

        Args:
            query: User query
            context: Retrieved context chunks
            system_prompt: Optional system prompt

        Returns:
            Generated answer
        """
        if not self.llm:
            logger.error("LLM adapter not configured")
            return ""

        try:
            # Build prompt
            context_text = "\n\n".join(context)

            if system_prompt is None:
                system_prompt = (
                    "You are a helpful assistant. Use the provided context "
                    "to answer the user's question. If you don't know the answer, "
                    "say so instead of making something up."
                )

            full_prompt = (
                f"{system_prompt}\n\n"
                f"Context:\n{context_text}\n\n"
                f"Question: {query}\n"
                f"Answer:"
            )

            # Generate answer
            answer = await self.llm.generate(
                prompt=full_prompt,
                max_tokens=512,
            )

            self.context_window.append({
                "query": query,
                "context": context,
                "answer": answer,
            })

            logger.info("Generated answer using LLM")
            return answer

        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return ""

    async def query(
        self,
        query: str,
        collection_name: str = "documents",
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """Full RAG query pipeline.

        Args:
            query: User query
            collection_name: Collection to search
            top_k: Number of retrieval results

        Returns:
            Dict with query, context, answer, and metadata
        """
        try:
            # Retrieve
            results = await self.retrieve(query, top_k, collection_name)
            context = [r["text"] for r in results]

            # Generate
            answer = await self.generate(query, context)

            return {
                "query": query,
                "answer": answer,
                "context": context,
                "retrieval_scores": [r.get("score", 0) for r in results],
                "num_results": len(results),
            }

        except Exception as e:
            logger.error(f"Error in RAG query: {e}")
            return {
                "query": query,
                "answer": "",
                "context": [],
                "retrieval_scores": [],
                "error": str(e),
            }

    def clear_context(self) -> None:
        """Clear conversation context window."""
        self.context_window = []
        logger.info("Cleared context window")

    def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of current context."""
        return {
            "messages": len(self.context_window),
            "history": self.context_window[-5:],  # Last 5 turns
        }
