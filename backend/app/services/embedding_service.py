"""Document embedding and vector database indexing service."""

import json
import logging
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


class VectorDatabaseManager:
    """Manage vector database operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.embeddings_stored = 0
    
    def store_embeddings(
        self,
        dependency_name: str,
        documents: List[Document],
        embeddings: List[List[float]],
    ) -> VectorStore:
        """
        Store embeddings in vector database record.
        
        Args:
            dependency_name: Name of dependency
            documents: List of Document objects
            embeddings: List of embedding vectors
            
        Returns:
            VectorStore record
        """
        # Get dependency from database
        dep = self.db.query(Dependency).filter(
            Dependency.name == dependency_name
        ).first()
        
        if not dep:
            logger.error(f"Dependency not found: {dependency_name}")
            return None
        
        # Check if VectorStore already exists
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
        
        # Update chunk count and mark as indexed
        vector_store.chunk_count = len(documents)
        vector_store.is_indexed = True
        vector_store.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(vector_store)
        
        logger.info(f"✓ Stored {len(documents)} vectors for {dependency_name}")
        self.embeddings_stored += 1
        
        return vector_store


async def embed_dependency_docs(
    db: Session,
    dependency_name: str,
    chunk_size: int = 1024,
    chunk_overlap: int = 300,
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
            return {
                "dependency": dependency_name,
                "status": "failed",
                "error": "Could not load documents",
                "chunks_created": 0,
            }
        
        # 2. Convert to texts
        texts = loader.documents_to_texts(raw_docs)
        if not texts:
            return {
                "dependency": dependency_name,
                "status": "failed",
                "error": "No valid text content found",
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
        
        # 4. Embed chunks
        embedder = DocumentEmbedder()
        if not embedder.embeddings:
            return {
                "dependency": dependency_name,
                "status": "failed",
                "error": "Ollama embeddings not available",
                "chunks_created": len(chunks),
            }
        
        embeddings = await embedder.embed_documents(chunks)
        
        if not embeddings:
            return {
                "dependency": dependency_name,
                "status": "failed",
                "error": "Failed to generate embeddings",
                "chunks_created": len(chunks),
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
        return {
            "dependency": dependency_name,
            "status": "error",
            "error": str(e),
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
    
    # Update user's SetupStatus
    setup = db.query(SetupStatus).filter(SetupStatus.user_id == user_id).first()
    if setup:
        all_successful = all(r["status"] == "completed" for r in results.values())
        setup.phase2_completed = all_successful
        setup.embeddings_status = "completed" if all_successful else "failed"
        setup.updated_at = datetime.utcnow()
        db.commit()
    
    return results
