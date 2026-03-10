import os
import sys
import json
import toml
import ollama
import asyncio
import aiofiles
import argparse
import re
from textwrap import fill
from pathlib import Path, PurePath
from typing import Tuple

# --- Imports ---
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import answer_relevancy, faithfulness, context_precision, context_recall
from ragas.llms import LangchainLLMWrapper
from langchain_community.vectorstores.pgvector import PGVector
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_core.prompts import PromptTemplate

# --- Helper Functions ---

def clean_text(text: str) -> str:
    """Cleans text by removing excess whitespace and non-ASCII characters."""
    if not isinstance(text, str): return ""
    cleaned = re.sub(r'\n\s*\n', '\n\n', text)
    cleaned = cleaned.encode("ascii", "ignore").decode("ascii")
    return cleaned.strip()

async def save_output_async(filepath, output_list):
    """Saves a list of strings to a file, one string per line."""
    async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
        await f.write("\n".join(output_list))

async def load_structured_input_async(filepath):
    """Loads a structured JSON input file."""
    async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:
        content = await f.read()
    if not content.strip():
        raise ValueError("Input JSON file is empty.")
    return json.loads(content)

async def load_toml_async(filepath):
    async with aiofiles.open(filepath, 'r') as config_file:
        content = await config_file.read()
    return toml.loads(content)

async def load_template_async(filepath):
    async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:
        raw_template_string = await f.read()
    return PromptTemplate.from_template(raw_template_string)

# --- Core RAG Functions ---

async def run_single_query(args, config_data, paths, model_config):
    """
    Runs the RAG pipeline for each query and its associated log file
    as defined in user_input.json.
    """
    print("--- Running RAG Application in Single Query Mode ---")

    language_model = model_config[args.model]["config"]
    hostname = config_data["database"]["ollama"]
    embedding_model = config_data[args.env]["embedding_models"][0]
    CONNECTION_STRING = config_data["settings"]["connection_string"]
    COLLECTION_NAME = config_data["settings"]["collection_name"]

    try:
        queries = await load_structured_input_async(paths["user_input"])
        prompt_template = await load_template_async(paths["prompt"])
    except Exception as e:
        print(f"Error loading input files: {e}", file=sys.stderr); return

    try:
        embeddings = OllamaEmbeddings(
            base_url=hostname, 
            model=embedding_model
        )
        db = PGVector(
            embedding_function=embeddings, 
            collection_name=COLLECTION_NAME, 
            connection_string=CONNECTION_STRING, 
            use_jsonb=True
        )
        client = ollama.Client(host=hostname)
    except Exception as e:
        print(f"Error during initialization: {e}", file=sys.stderr); return

    output_list = []
    for query_obj in queries:
        question = query_obj.get("question", "").strip()
        log_filename = query_obj.get("log_file", None)

        print("\n" + "🔍 QUERY".center(100, "="))
        print(fill(question, width=100))

        log_content = ""
        error_summary = ""
        if log_filename:
            log_path = paths["data"] / log_filename
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    log_content = f.read()
            except FileNotFoundError:
                print(f"--> WARNING: Log file '{log_path}' not found.")

            error_lines = re.findall(r'^(?:ERROR|Traceback|TypeError|RuntimeError|ValueError)[\s\S]*?(?=\n\w|\Z)', log_content, re.MULTILINE)
            error_summary = "\n".join(error_lines)

        enriched_query = f"{question}\n\nKey Error from Log:\n{error_summary}"
        results = db.similarity_search_with_score(enriched_query, k=3)
        retrieved_contexts = [doc.page_content for doc, score in results]

        log_section = f"Log Content:\n{log_content.strip()}" if log_content else "Log Content: [None provided]"
        docs_section = (
            "Retrieved Documentation:\n" + "\n---\n".join(retrieved_contexts)
            if retrieved_contexts else "Retrieved Documentation: [None found]"
        )
        combined_context = f"{log_section}\n\n{docs_section}"

        final_prompt = prompt_template.format(context=combined_context, question=question)
        print("\n[DEBUG] Final Prompt Sent to LLM:\n")
        print(final_prompt)

        try:
            response = client.generate(
                model=language_model, 
                prompt=final_prompt, 
                options={"temperature": 0.2}
            )
            response_text = response.get('response', '').strip()
        except Exception as e:
            response_text = f"Error generating response: {e}"

        print("\n" + "=" * 100)
        print("🔍 QUERY".center(100, " "))
        print("=" * 100)
        print(fill(clean_text(question), width=100))
        print("\n" + "=" * 100)
        print("🧠 ASSISTANT RESPONSE".center(100, " "))
        print("=" * 100)
        print(fill(clean_text(response_text), width=100))

        output_list.extend([
            "=" * 100,
            "🔍 QUERY".center(100, " "),
            "=" * 100,
            fill(clean_text(question), width=100),
            "",
            "=" * 100,
            "🧠 ASSISTANT RESPONSE".center(100, " "),
            "=" * 100,
            fill(clean_text(response_text), width=100),
            ""
        ])
        if results:
            print("\n" + "=" * 100)
            print("📚 RETRIEVED DOCUMENTATION".center(100, " "))
            print("=" * 100)
            for i, (doc, score) in enumerate(results, 1):
                cleaned = doc.page_content.encode().decode("unicode_escape").strip()
                block_header = f"📌 EXTRACT #{i} | 🔢 Similarity Score: {round(score, 3)}"
                block_sep = "─" * 100
                print("\n" + block_sep)
                print(block_header.center(100, " "))
                print(block_sep)
                print(fill(clean_text(cleaned), width=100))
                output_list.extend([
                    "",
                    block_sep,
                    block_header.center(100, " "),
                    block_sep,
                    fill(clean_text(cleaned), width=100),
                    ""
                ])
            print("\n" + "=" * 100)
            print("END OF OUTPUT".center(100, " "))
            print("=" * 100)
            output_list.extend([
                "",
                "=" * 100,
                "END OF OUTPUT".center(100, " "),
                "=" * 100
            ])
        else:
            print("\nNo relevant documents were retrieved.")
            output_list.append("\n(No relevant documents were retrieved.)")

    await asyncio.sleep(1)
    await save_output_async(paths["output"], output_list)
    print(f"\n✅ Results saved to {paths['output']}")

async def run_evaluation(args, config_data, paths, model_config):
    """
    Runs the full, slow RAGAs evaluation against the eval_dataset.json file.
    """
    print("--- Running RAG Application in Evaluation Mode ---")
    
    embedding_model = config_data[args.env]["embedding_models"][0]
    language_model = model_config[args.model]['config']
    hostname = config_data["database"]["ollama"]
    CONNECTION_STRING = config_data["settings"]["connection_string"]
    COLLECTION_NAME = config_data["settings"]["collection_name"]
    
    try:
        embeddings = OllamaEmbeddings(
            base_url=hostname, 
            model=embedding_model
            )
        db = PGVector(
            embedding_function=embeddings, 
            collection_name=COLLECTION_NAME, 
            connection_string=CONNECTION_STRING, 
            use_jsonb=True
            )

        with open(paths["eval_data"], 'r', encoding='utf-8') as f:
            eval_data = json.load(f)

        prompt_template = await load_template_async(paths["prompt"])
        client = ollama.Client(host=hostname)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize for evaluation: {e}")

    questions_list, ground_truths_list, contexts_list, predictions_list = [], [], [], []

    for item in eval_data:
        question = item["question"]
        ground_truth = item["ground_truth"]
        results_with_scores = db.similarity_search_with_score(question, k=10)
        # TUNE THIS THRESHOLD FOR HIGHER PRECISION
        DISTANCE_THRESHOLD = 0.3  # Lower threshold for more relevant docs
        high_quality_docs = [doc for doc, score in results_with_scores if score < DISTANCE_THRESHOLD]
        final_docs = high_quality_docs[:2]  # Reduce top_k to 2 for more focused context
        retrieved_contexts = [doc.page_content for doc in final_docs]
        context_string = "\n---\n".join(retrieved_contexts)

        final_prompt = prompt_template.format(context=context_string, question=question)
        response_text = ""
        try:
            response = client.generate(
                model=language_model, 
                prompt=final_prompt, 
                options={"temperature": 0.2}
            )
            response_text = response.get('response', '').strip()
        except Exception:
            response_text = "Error generating response."

        questions_list.append(question)
        ground_truths_list.append(ground_truth)
        contexts_list.append(retrieved_contexts)
        predictions_list.append(response_text)
        print(f"Processed query: {question[:80]}...")

    print("\n--- Aggregating results for Ragas Evaluation ---")
    ragas_dataset = Dataset.from_dict({
        "question": questions_list,
        "answer": predictions_list,
        "contexts": contexts_list,
        "ground_truth": ground_truths_list,
    })
    
    try:
        # Increase timeout for OllamaLLM used in RAGAS
        ollama_llm_for_ragas = OllamaLLM(base_url=hostname, model=language_model, timeout=300)
        llm_wrapper = LangchainLLMWrapper(ollama_llm_for_ragas)
        metrics = [answer_relevancy, faithfulness, context_precision, context_recall]
        ragas_results = evaluate(ragas_dataset, metrics=metrics, llm=llm_wrapper, embeddings=embeddings)
        print("\n--- FINAL RAGAS EVALUATION SCORES ---")
        print(ragas_results)
    except Exception as e:
        print(f"Ragas evaluation failed: {e}")

async def process_query(
    log_content: str,
    user_question: str,
    config: dict,
    model_name: str,
    embedding_model: str,
    system_prompt: str = None,
    top_k: int = 3
) -> Tuple[str, list]:
    """
    Process a single query using provided log content and user question.
    Returns the generated response text and similarity search results.
    """
    connection_string = config["settings"]["connection_string"]
    collection_name = config["settings"]["collection_name"]
    hostname = config["database"]["ollama"]

    try:
        embeddings = OllamaEmbeddings(
            base_url=hostname,
            model=embedding_model,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to initialize embeddings: {e}")

    db = PGVector(
        embedding_function=embeddings,
        collection_name=collection_name,
        connection_string=connection_string,
        use_jsonb=True,
    )
    await asyncio.sleep(1)

    results = db.similarity_search_with_score(user_question, k=top_k)
    print(f"Debug: Similarity search returned {len(results)} results.")

    if system_prompt is None:
        system_prompt = user_question

    log_section = f"Log Content:\n{log_content.strip()}\n" if log_content.strip() else ""
    docs_section = "\n---\n".join([doc.page_content for doc, _ in results])
    docs_section = f"Retrieved Documents:\n{docs_section}" if docs_section else ""
    combined_context = "\n\n".join([s for s in [log_section, docs_section] if s])
    user_prompt = f"Context:\n{combined_context}\n\nQuestion: {user_question}"

    client = ollama.Client(host=hostname)
    try:
        response = client.generate(
            model=model_name,
            prompt=user_prompt,
            options={"temperature": 0.5},
        )
        response_text = response.get('response', '').strip()
    except Exception as e:
        response_text = f"An error occurred while processing your request: {e}"

    return response_text, results 

# --- Main Controller ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A RAG application for CI/CD log analysis.")
    parser.add_argument('--env', type=str, required=True, choices=['lab_model', 'dgx_model'])
    parser.add_argument('--model', type=str, required=True)
    parser.add_argument('--evaluate', action='store_true', help='If set, runs the RAGAs evaluation.')
    args = parser.parse_args()

    model_config = {
        'my_mistral:latest':{'dir': 'mistral', 'config': 'my_mistral:latest'},
        'mistral:7b':       {'dir': 'mistral', 'config': 'mistral:7b'},
        'llama3.2:3b':      {'dir': 'llama3', 'config': 'llama3.2:3b'},
        'gemma3:27b':       {'dir': 'gemma3', 'config': 'gemma3:27b'},
        'llama4':           {'dir': 'llama4', 'config': 'llama4'},
        'my_llama4:latest': {'dir': 'llama4', 'config': 'my_llama4:latest'}
    }

    try:
        PROJECT_ROOT = Path(__file__).resolve().parent.parent
        MODEL_DIR = model_config[args.model]['dir']
        DATADIR = PROJECT_ROOT / 'data'
        PATHS = {
            "prompt":      PROJECT_ROOT / "ollama_build" / args.env / MODEL_DIR / "template.txt",
            "config":      PROJECT_ROOT / "src" / "config.toml",
            "data":        DATADIR / "logs",
            "output":      DATADIR / "outputs" / "query_results.txt",
            "user_input":  DATADIR / "inputs" / "user_input.json",
            "eval_data":   PROJECT_ROOT / "src" / "eval_dataset.json"
        }
    except KeyError:
        print(f"Error: Model '{args.model}' not found in model_config.", file=sys.stderr)
        sys.exit(1)

    for k, p in PATHS.items():
        print(f"{k:<20}: {p}\n")

    async def main():
        try:
            config = await load_toml_async(PATHS["config"])
            if args.evaluate:
                await run_evaluation(args, config, PATHS, model_config)
            else:
                await run_single_query(args, config, PATHS, model_config)
        except Exception as e:
            print(f"An unexpected error occurred in main: {e}", file=sys.stderr); sys.exit(1)

    asyncio.run(main())

