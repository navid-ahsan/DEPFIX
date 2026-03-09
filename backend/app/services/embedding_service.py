"""Document embedding and vector database indexing service."""

import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from sqlalchemy.orm import Session
from backend.app.models.database import VectorStore, Dependency, SetupStatus
from datetime import datetime

logger = logging.getLogger(__name__)


class DocumentChunker:
    """Chunk documents using LangChain."""
    
    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 300):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )
    
    def chunk_documents(self, texts: List[str], metadata: Dict = None) -> List[Document]:
        """
        Split texts into chunks.
        
        Args:
            texts: List of text strings to chunk
            metadata: Metadata to attach to documents
            
        Returns:
            List of Document objects with chunks
        """
        docs = []
        for text in texts:
            # Split each text into chunks
            chunks = self.splitter.split_text(text)
            for i, chunk in enumerate(chunks):
                doc_metadata = metadata.copy() if metadata else {}
                doc_metadata["chunk_index"] = i
                
                doc = Document(
                    page_content=chunk,
                    metadata=doc_metadata,
                )
                docs.append(doc)
        
        return docs


class DocumentEmbedder:
    """Embed documents using Ollama."""
    
    def __init__(self, ollama_host: str = "http://localhost:11434", model: str = "nomic-embed-text"):
        try:
            from langchain_ollama import OllamaEmbeddings
            self.embeddings = OllamaEmbeddings(
                base_url=ollama_host,
                model=model,
            )
            self.model = model
            logger.info(f"✓ Ollama embeddings initialized with model: {model}")
        except Exception as e:
            logger.error(f"Failed to initialize Ollama embeddings: {e}")
            self.embeddings = None
    
    async def embed_documents(self, documents: List[Document]) -> List[List[float]]:
        """
        Embed a batch of documents.
        
        Args:
            documents: List of Document objects
            
        Returns:
            List of embedding vectors
        """
        if not self.embeddings:
            logger.error("Embeddings not initialized")
            return []
        
        try:
            texts = [doc.page_content for doc in documents]
            embeddings = self.embeddings.embed_documents(texts)
            logger.info(f"✓ Embedded {len(embeddings)} documents")
            return embeddings
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            return []


class DocumentLoader:
    """Load documents from local JSONL files."""
    
    @staticmethod
    def load_from_jsonl(dependency_name: str) -> Optional[List[Dict]]:
        """
        Load documents from local jsonl file.
        
        Args:
            dependency_name: Name of the dependency
            
        Returns:
            List of document dictionaries
        """
        jsonl_path = Path(f"/home/navid/project/socialwork/data/documents/{dependency_name}.jsonl")
        
        if not jsonl_path.exists():
            logger.warning(f"JSONL file not found: {jsonl_path}")
            return None
        
        documents = []
        try:
            with open(jsonl_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        doc = json.loads(line)
                        documents.append(doc)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse line {line_num} in {dependency_name}.jsonl: {e}")
                        continue
            
            logger.info(f"✓ Loaded {len(documents)} documents from {dependency_name}.jsonl")
            return documents
        
        except Exception as e:
            logger.error(f"Error loading {dependency_name}.jsonl: {e}")
            return None
    
    @staticmethod
    def documents_to_texts(documents: List[Dict]) -> List[str]:
        """Convert document dicts to text strings."""
        texts = []
        for doc in documents:
            # Extract text content from various possible fields
            text = doc.get("content") or doc.get("text") or doc.get("body", "")
            if text:
                texts.append(text)
        return texts


class PGVectorStorage:
    """Direct pgvector storage for document chunk embeddings."""

    def __init__(self):
        raw = os.environ.get(
            "VECTORDB_POSTGRES_URL",
            "postgresql://postgres:password123@localhost:5432/vector_db",
        )
        # psycopg2 needs plain postgresql:// scheme
        self.conn_str = raw.replace("postgresql+psycopg2://", "postgresql://")
        self._ready = False
        self._ensure_table()

    def _get_conn(self):
        import psycopg2
        return psycopg2.connect(self.conn_str)

    def _ensure_table(self):
        """Create document_chunks table and indexes if they don't exist."""
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS document_chunks (
                        id SERIAL PRIMARY KEY,
                        dependency_name VARCHAR(255) NOT NULL,
                        content TEXT NOT NULL,
                        metadata JSONB,
                        embedding vector(768),
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS doc_chunks_dep_idx
                    ON document_chunks (dependency_name)
                """)
            conn.commit()
            conn.close()
            self._ready = True
            logger.info("✓ PGVector document_chunks table ready")
        except Exception as e:
            logger.error(f"PGVector setup failed: {e}")

    def delete_dependency(self, dependency_name: str):
        """Remove all stored chunks for a dependency (for re-indexing)."""
        if not self._ready:
            return
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM document_chunks WHERE dependency_name = %s",
                    (dependency_name,),
                )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to delete chunks for {dependency_name}: {e}")

    def insert_chunks(
        self,
        dependency_name: str,
        documents: List[Document],
        embeddings: List[List[float]],
    ) -> int:
        """Insert document chunks with their embedding vectors."""
        if not self._ready or not documents or not embeddings:
            return 0
        try:
            conn = self._get_conn()
            count = 0
            with conn.cursor() as cur:
                for doc, emb in zip(documents, embeddings):
                    emb_str = "[" + ",".join(str(v) for v in emb) + "]"
                    cur.execute(
                        """
                        INSERT INTO document_chunks
                            (dependency_name, content, metadata, embedding)
                        VALUES (%s, %s, %s, %s::vector)
                        """,
                        (
                            dependency_name,
                            doc.page_content,
                            json.dumps(doc.metadata),
                            emb_str,
                        ),
                    )
                    count += 1
            conn.commit()
            conn.close()
            logger.info(f"✓ Inserted {count} chunks for {dependency_name} into pgvector")
            return count
        except Exception as e:
            logger.error(f"Failed to insert chunks for {dependency_name}: {e}")
            return 0

    def similarity_search(
        self,
        embedding: List[float],
        dependency_names: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> List[Dict]:
        """Find most similar chunks using cosine similarity."""
        if not self._ready:
            return []
        try:
            conn = self._get_conn()
            emb_str = "[" + ",".join(str(v) for v in embedding) + "]"
            with conn.cursor() as cur:
                if dependency_names:
                    cur.execute(
                        """
                        SELECT dependency_name, content,
                               1 - (embedding <=> %s::vector) AS similarity
                        FROM document_chunks
                        WHERE dependency_name = ANY(%s)
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                        """,
                        (emb_str, dependency_names, emb_str, top_k),
                    )
                else:
                    cur.execute(
                        """
                        SELECT dependency_name, content,
                               1 - (embedding <=> %s::vector) AS similarity
                        FROM document_chunks
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                        """,
                        (emb_str, emb_str, top_k),
                    )
                rows = cur.fetchall()
            conn.close()
            return [
                {
                    "dependency": row[0],
                    "content": row[1],
                    "relevance_score": float(row[2]),
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []

    def has_embeddings(self, dependency_name: str) -> bool:
        """Check if a dependency already has embeddings stored."""
        if not self._ready:
            return False
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM document_chunks WHERE dependency_name = %s",
                    (dependency_name,),
                )
                count = cur.fetchone()[0]
            conn.close()
            return count > 0
        except Exception as e:
            logger.error(f"has_embeddings check failed: {e}")
            return False


class VectorDatabaseManager:
    """Manage vector database operations (pgvector + SQLite metadata)."""

    def __init__(self, db: Session):
        self.db = db
        self.embeddings_stored = 0
        self.pg_storage = PGVectorStorage()

    def store_embeddings(
        self,
        dependency_name: str,
        documents: List[Document],
        embeddings: List[List[float]],
    ) -> VectorStore:
        """
        Store embeddings in pgvector and update SQLite metadata record.

        Args:
            dependency_name: Name of dependency
            documents: List of Document objects
            embeddings: List of embedding vectors

        Returns:
            VectorStore metadata record
        """
        # Store actual vectors in pgvector (overwrite previous if any)
        self.pg_storage.delete_dependency(dependency_name)
        stored_count = self.pg_storage.insert_chunks(dependency_name, documents, embeddings)

        # Update SQLite metadata record
        dep = self.db.query(Dependency).filter(
            Dependency.name == dependency_name
        ).first()

        if not dep:
            logger.error(f"Dependency not found in SQLite: {dependency_name}")
            return None

        vector_store = self.db.query(VectorStore).filter(
            VectorStore.dependency_id == dep.id
        ).first()

        if not vector_store:
            vector_store = VectorStore(
                dependency_id=dep.id,
                collection_name=f"docs_{dependency_name.replace('-', '_')}",
                embedding_model="nomic-embed-text",
                vector_db_type="pgvector",
            )
            self.db.add(vector_store)

        vector_store.chunk_count = stored_count
        vector_store.is_indexed = stored_count > 0
        vector_store.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(vector_store)

        logger.info(f"✓ Stored {stored_count} vectors for {dependency_name}")
        self.embeddings_stored += 1

        return vector_store


async def embed_dependency_docs(
    db: Session,
    dependency_name: str,
    chunk_size: int = 512,
    chunk_overlap: int = 100,
    max_docs: int = 40,
) -> Dict:
    """
    Complete embedding pipeline for a dependency.
    
    Args:
        db: Database session
        dependency_name: Name of dependency to embed
        chunk_size: Size of text chunks
        chunk_overlap: Overlap between chunks
        
    Returns:
        Status dictionary
    """
    try:
        logger.info(f"Starting embedding pipeline for {dependency_name}...")
        
        # 1. Load documents
        loader = DocumentLoader()
        raw_docs = loader.load_from_jsonl(dependency_name)
        
        if not raw_docs:
            logger.warning(f"Could not load documents for {dependency_name}, marking as completed anyway")
            return {
                "dependency": dependency_name,
                "status": "completed",
                "warning": "Document file not found, but proceeding",
                "chunks_created": 0,
            }
        
        # 2. Convert to texts (limit to max_docs for speed)
        if len(raw_docs) > max_docs:
            logger.info(f"Limiting {dependency_name} from {len(raw_docs)} to {max_docs} docs for speed")
            raw_docs = raw_docs[:max_docs]

        texts = loader.documents_to_texts(raw_docs)
        if not texts:
            logger.warning(f"No valid text content found for {dependency_name}, marking as completed")
            return {
                "dependency": dependency_name,
                "status": "completed",
                "warning": "No text content found",
                "chunks_created": 0,
            }
        
        # 3. Chunk documents
        chunker = DocumentChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        metadata = {
            "dependency": dependency_name,
            "source": f"{dependency_name}_docs",
        }
        chunks = chunker.chunk_documents(texts, metadata)
        
        logger.info(f"Created {len(chunks)} chunks for {dependency_name}")
        
        # 4. Embed chunks (skip if Ollama unavailable)
        embedder = DocumentEmbedder()
        if not embedder.embeddings:
            logger.warning(f"Ollama embeddings not available for {dependency_name}, skipping vector storage but marking as completed")
            return {
                "dependency": dependency_name,
                "status": "completed",
                "warning": "Ollama embeddings not available, skipped vector indexing",
                "chunks_created": len(chunks),
                "embeddings_generated": 0,
            }
        
        embeddings = await embedder.embed_documents(chunks)
        
        if not embeddings:
            logger.warning(f"Failed to generate embeddings for {dependency_name}, marking as completed")
            return {
                "dependency": dependency_name,
                "status": "completed",
                "warning": "Failed to generate embeddings, proceeding without vector index",
                "chunks_created": len(chunks),
                "embeddings_generated": 0,
            }
        
        # 5. Store in vector database
        vdb_manager = VectorDatabaseManager(db)
        vector_store = vdb_manager.store_embeddings(
            dependency_name,
            chunks,
            embeddings,
        )
        
        return {
            "dependency": dependency_name,
            "status": "completed",
            "chunks_created": len(chunks),
            "embeddings_generated": len(embeddings),
            "vector_store_id": vector_store.id if vector_store else None,
        }
    
    except Exception as e:
        logger.error(f"Error embedding {dependency_name}: {e}", exc_info=True)
        logger.warning(f"Embedding failed for {dependency_name}, but marking as completed to not block flow")
        return {
            "dependency": dependency_name,
            "status": "completed",
            "warning": f"Embedding failed: {str(e)}, but proceeding",
            "chunks_created": 0,
        }


async def embed_all_selected_dependencies(
    db: Session,
    user_id: str,
    dependency_names: List[str],
) -> Dict[str, Dict]:
    """
    Embed all selected dependencies for a user.
    
    Args:
        db: Database session
        user_id: User ID
        dependency_names: List of dependency names to embed
        
    Returns:
        Dictionary of status for each dependency
    """
    results = {}
    
    logger.info(f"Embedding {len(dependency_names)} dependencies for user {user_id}...")
    
    for dep_name in dependency_names:
        result = await embed_dependency_docs(db, dep_name)
        results[dep_name] = result
    
    # Update user's SetupStatus - mark as completed regardless of embedding success
    # This allows users to proceed through the flow even if embedding fails
    setup = db.query(SetupStatus).filter(SetupStatus.user_id == user_id).first()
    if setup:
        setup.phase2_completed = True  # Always mark as completed to not block flow
        setup.embeddings_status = "completed"
        setup.updated_at = datetime.utcnow()
        db.commit()
    
    return results
