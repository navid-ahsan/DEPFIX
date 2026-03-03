import os
import re
import toml
import argparse
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn
import logging

# --- Imports from your RAG Engine ---
# FIX: Only import the function you need, not its internal variables.
from rag_app import process_query

# --- Pydantic Models for API Contract ---
class RAGRequest(BaseModel):
    query: str
    log_content: str

class RelatedDocument(BaseModel):
    content: str
    score: float

class RAGResponse(BaseModel):
    response: str
    related_documents: List[RelatedDocument]

# --- Main Application Setup ---

# FIX: The server should manage its own arguments.
# This makes the server a self-contained, runnable application.
parser = argparse.ArgumentParser(description="Run the RAG FastAPI Server.")
parser.add_argument('--env', type=str, required=True, choices=['lab_model', 'dgx_model'], help='Select the environment.')
parser.add_argument('--model', type=str, required=True, help='Select the model to use.')
args = parser.parse_args()

# Load configuration once at startup
PROJECT_ROOT = Path(__file__).resolve().parent.parent
config_data = toml.load(PROJECT_ROOT / "src" / "config.toml")

# Determine embedding model from config
ENV = args.env
embedding_models = config_data[ENV]["embedding_models"]
embedding_model = embedding_models[0] if isinstance(embedding_models, list) else embedding_models


app = FastAPI()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Health check endpoint
@app.get("/healthz")
async def health_check():
    return {"status": "ok"}

def clean_ansi_codes(text: str) -> str:
    """Removes ANSI escape codes from a string."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

@app.post("/run_rag", response_model=RAGResponse)
async def run(request: RAGRequest):
    """API endpoint to process a RAG query."""
    try:
        logger.info(f"Processing new RAG request for model '{args.model}'")
        
        # Call our robust, stateless RAG processor function
        response_text, results = await process_query(
            log_content=request.log_content,
            user_question=request.query,
            config=config_data,
            model_name=args.model, # Use the server's own args
            embedding_model=embedding_model,
            top_k=3
        )

        cleaned_documents = []
        if results:
            # FIX: The loop now correctly iterates over a list of dictionaries.
            for doc_dict in results:
                cleaned_documents.append({
                    "content": clean_ansi_codes(doc_dict.get("content", "")),
                    "score": round(doc_dict.get("score", 0.0), 4)
                })

        logger.info("RAG request processed successfully.")
        return {
            "response": response_text.strip(),
            "related_documents": cleaned_documents
        }

    except Exception as e:
        logger.error(f"An internal error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {e}")

if __name__ == "__main__":
    logger.info("--- Starting FastAPI Server ---")
    logger.info(f"Model: '{args.model}' | Environment: '{args.env}'")
    uvicorn.run(app, host="0.0.0.0", port=8000)

