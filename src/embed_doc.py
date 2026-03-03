import os
import json
import toml
from pathlib import Path
from sqlalchemy import create_engine, text
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.pgvector import PGVector
from langchain_ollama import OllamaEmbeddings
import logging

# --- Configuration & Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

config_data = toml.load(os.path.join(os.path.dirname(__file__), "config.toml"))

DATA_DIR = Path("./data/documents") 
DB_CONFIG = config_data["database"]
SETTINGS_CONFIG = config_data["settings"]
connection_string = SETTINGS_CONFIG["connection_string"]
collection_name = SETTINGS_CONFIG["collection_name"]
embedding_models = config_data["lab_model"]["embedding_models"]
embedding = embedding_models[1] # "nomic-embed-text"

# --- 1. Load Documents ---
# Simplified loading logic assuming one JSON object per line, which is standard for .jsonl
all_docs = []
for doc_path in DATA_DIR.glob("*.jsonl"):
    logger.info(f"Processing file: {doc_path.name}")
    with open(doc_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                # This handles both single documents and lists of documents from your scraper
                if isinstance(data, list):
                    items = data
                else:
                    items = [data]
                
                for item in items:
                    if isinstance(item, dict) and "content" in item:
                        # Use metadata from the scraping script (library, source URL)
                        all_docs.append(Document(
                            page_content=item.get("content"),
                            metadata={
                                "library": item.get("library", "unknown"),
                                "source": item.get("source", "unknown")
                            }
                        ))
            except json.JSONDecodeError:
                logger.warning(f"Skipping malformed line in {doc_path.name}")

# --- 2. Chunk Documents ---
logger.info(f"Total documents loaded: {len(all_docs)}")
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=SETTINGS_CONFIG["chunk_size"],
    chunk_overlap=SETTINGS_CONFIG["chunk_overlap"]
)
chunks = text_splitter.split_documents(all_docs)
logger.info(f"Total chunks created: {len(chunks)}")


# --- 3. Storing in Vector DB ---
logger.info("Initializing Ollama embeddings...")
embeddings = OllamaEmbeddings(
    model = embedding,
    base_url=f"{DB_CONFIG['ollama']}"
)
logger.info(f"Embedding model: {embeddings.model}")

# This manual deletion is a good strategy for development to ensure a clean slate.
logger.info(f"Checking for and removing existing collection '{collection_name}'...")
engine = create_engine(connection_string)
with engine.connect() as conn:
    conn.execute(text(f"DROP TABLE IF EXISTS langchain_pg_collection CASCADE;"))
    conn.execute(text(f"DROP TABLE IF EXISTS langchain_pg_embedding CASCADE;"))
    conn.commit()
logger.info("Schema cleaned.")

logger.info("Storing chunks in PGVector. This may take a while...")
vector_store = PGVector.from_documents(
    embedding=embeddings,
    documents=chunks,
    collection_name=collection_name,
    connection_string=connection_string,
    use_jsonb=True, # Recommended for flexible metadata filtering
)
logger.info("✅ Ingestion complete!")

# --- 4. Best Practice for Large Datasets ---
# For very large numbers of documents, process them in batches to avoid high memory usage.
# The `from_documents` method is great for starting, but `add_documents` is better for scaling.
# Example:
#
# # First, create the store with the first batch
# vector_store = PGVector.from_documents(chunks[:1000], ...)
#
# # Then, add subsequent batches
# for i in range(1000, len(chunks), 1000):
#     vector_store.add_documents(chunks[i:i+1000])
#     logger.info(f"Added batch {i} to vector store.")