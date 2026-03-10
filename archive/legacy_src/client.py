import asyncio
import httpx  # Modern async HTTP client, replacement for 'requests'
from pathlib import Path
import textwrap
import os
import re
import aiofiles
import json
import logging
import unicodedata

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
# Use an environment variable for the server URL, falling back to a default.
# This makes it easy to point the client to the DGX without changing the code.
SERVER_URL = os.environ.get("RAG_SERVER_URL", "http://172.24.54.47:8000/run_rag")

# Use an environment variable for the project root for reliability.
# This allows the client to locate the necessary files regardless of the current working directory.
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = os.environ.get("PROJECT_ROOT", SCRIPT_DIR.parent)

log_dir = PROJECT_ROOT / "data" / "logs"
questions_path = PROJECT_ROOT / "data" / "inputs" / "user_input.json"
output_dir = PROJECT_ROOT / "data" / "output"
output_file = output_dir / "output.log"


async def read_questions(filepath):
    """Loads a structured JSON input file."""
    async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:
        content = await f.read()
    if not content.strip():
        logger.warning("Input JSON file is empty.")
    return json.loads(content)

# Asynchronous function to process each RAG request
async def async_rag_process(client: httpx.AsyncClient, log_content: str, user_question: str):
    """
    Sends a single request asynchronously to the RAG server.
    """
    payload = {"query": user_question, "log_content": log_content}
    try:
        response = await client.post(SERVER_URL, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Received response for question: {user_question[:50]}...")
        return user_question, data.get("response", ""), data.get("related_documents", [])
    except httpx.RequestError as e:
        logger.error(f"Failed to contact the API for question '{user_question}': {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response status code: {e.response.status_code}")
            logger.error(f"Response content: {e.response.text}")
        return user_question, f"Error: Failed to get response from server. Details: {str(e)}", []

# Main asynchronous function to handle the RAG processing
async def main():
    """
    Main execution block: reads data, creates concurrent tasks for all questions,
    runs them at once, and then prints all results.
    """
    try:
        queries = await read_questions(questions_path)
    except Exception as e:
        logger.error(f"Error reading questions from {questions_path}: {e}")
        return []

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks = []
    async with httpx.AsyncClient() as client:
        logger.info(f"Preparing to send {len(queries)} questions concurrently to {SERVER_URL}...")
        for query_obj in queries:
            question_text = query_obj.get("question", "").strip()
            log_filename = query_obj.get("log_file", "").strip()
            log_content = ""
            if log_filename:
                log_path = log_dir / log_filename
                if not log_path.exists():
                    logger.error(f"Log file does not exist: {log_path}")
                    log_content = f"Log file not found: {log_path}"
                else:
                    try:
                        async with aiofiles.open(log_path, 'r', encoding='utf-8') as f:
                            log_content = await f.read()
                    except Exception as e:
                        logger.error(f"Error reading log file {log_path}: {e}")
                        log_content = f"Error reading log file: {e}"
            else:
                logger.warning(f"No log file specified for question: {question_text}")
            # Create a task for each question and add it to our list
            task = async_rag_process(client, log_content, question_text)
            tasks.append(task)

        # asyncio.gather runs all the tasks in our list concurrently.
        results = await asyncio.gather(*tasks)

    logger.info("All responses received.")
    return results

if __name__ == "__main__":
    # Capture the returned results
    results = asyncio.run(main())

    # Cleaning the results
    def clean_text(text):
        text = text.strip()
        text = unicodedata.normalize("NFKD", text)
        return text

    # Saving the response in data/output 
    with open(output_file, "w", encoding="utf-8") as f:
        for user_question, response_text, related_documents in results or []:
            f.write("\n" + "Question".center(100, "=") + "\n" + user_question[:207] + "\n")
            f.write("\n" + "RAG Response".center(100, "=") + "\n" + response_text + "\n")
            f.write("\n" + "📚 RELATED DOCUMENTATION".center(100, "=") + "\n")
            if related_documents:
                for idx, doc in enumerate(related_documents, 1):
                    score = doc.get('score', 0.0)
                    content = doc.get('content', '')
                    cleaned = clean_text(content)
                    temp_cleaned = textwrap.fill(cleaned, width=100)
                    f.write(f"📌 EXTRACT #{idx} | 🔢 Similarity Score: {round(float(score), 3)}\n")
                    f.write(temp_cleaned + "\n")
                f.write("\n" + "=" * 100 + "\n")
            else:
                f.write("\n(No related documentation found.)\n")

    logger.info(f"Results saved to {output_file}")
