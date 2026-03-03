import os
import re
import sys
import json
import toml
import ollama
import asyncio
import aiofiles
import argparse
from textwrap import fill
from pathlib import Path, PurePath
from typing import Tuple
# --- Imports ---
from datasets import Dataset
from pydantic import BaseModel
from ragas import evaluate
from ragas.metrics import answer_relevancy, faithfulness, context_precision, context_recall
from ragas.llms import LangchainLLMWrapper
from langchain_community.vectorstores.pgvector import PGVector
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_core.prompts import PromptTemplate
# This allows users to specify the environment and model to use when running the application.

parser = argparse.ArgumentParser(description="Run the RAG application.")

parser.add_argument('--env', type=str, required=True,
                    choices=['lab_model', 'dgx_model'], 
                    help='Select the environment: lab_model or dgx_model')


parser.add_argument('--model', type=str, required=True,
                    help='Select the model to use')


parser.add_argument('--build-model', action='store_true',
                    help='Build the models if specified')

parser.add_argument('--evaluate', action='store_true', 
                    help='If set, runs the RAGAs evaluation.')

args = parser.parse_args()


# It allows for easy retrieval of model paths and configurations based on the selected model.
# The keys are model names, and the values are dictionaries containing 'dir' and 'config

model_config = {
    'my_mistral:latest':{'dir': 'mistral', 'config': 'my_mistral:latest'},
    'mistral:7b':       {'dir': 'mistral', 'config': 'mistral:7b'},
    'llama3.2:3b':      {'dir': 'llama3', 'config': 'llama3.2:3b'},
    'gemma3:27b':       {'dir': 'gemma3', 'config': 'gemma3:27b'},
    'llama4':           {'dir': 'llama4', 'config': 'llama4'},
    'my_llama4:latest': {'dir': 'llama4', 'config': 'my_llama4:latest'}
}

# Path configurations
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", Path(__file__).resolve().parent.parent))
MODEL_DIR = model_config[args.model]['dir']
TEMPLATE_PATH = Path(os.path.join(PROJECT_ROOT, "ollama_build", args.env, MODEL_DIR, "template.txt"))
DATADIR = Path(os.path.join(PROJECT_ROOT, 'data'))


if args.build_model:
    if args.model not in model_config:
        print(f"Error: Model '{args.model}' not found in model config.", file=sys.stderr)
        sys.exit(1)
    
    config = model_config[args.model]

    model_name_to_create = config['config']
    from_model = args.model
    print(from_model)
    if args.model == from_model:
        print(f"MODEL_NAME_TO_CREATE={model_name_to_create}")
        print(f"MODELFILE_CONTENT=FROM {from_model}")
else:
    # Run the actual RAG application
    print(f"--- Running RAG Application ---")
    print(f"Using Model: {args.model} in Environment: {args.env}")


# Check environment and model combination

if args.env == 'dgx_model' and args.model in ['gemma3:27b', 'llama4', 'my_llama4:latest']:
    print(f'Using DGX model: {args.model}')

elif args.env == 'lab_model' and args.model in ['my_mistral:latest', 'mistral:7b', 'llama3.2:3b']:
    print(f'Using Lab model: {args.model}')

else:
    print(f"Invalid combination: env={args.env}, model={args.model}")
    exit(1)
# Print paths for verification
print(f"Project root: {PROJECT_ROOT}\n")


# Paths Definition
PATHS = {
    "prompt": PurePath(TEMPLATE_PATH),
    "config": PurePath(PROJECT_ROOT, "src", "config.toml"),
    "data": PurePath(DATADIR, "logs"),
    "output": PurePath(DATADIR, "outputs", "query_results.txt"),
    "user_input": PurePath(DATADIR, "inputs", "user_input.json"),
    "eval_data": PurePath(PROJECT_ROOT, "src", "eval_dataset.json")
}

for k, p in PATHS.items():
    print(f"{k:<20}: {p}\n")


# Async function to load TOML configuration
async def load_toml_async():
    async with aiofiles.open(PATHS["config"], 'r') as config_file:
        content = await config_file.read()
    return toml.loads(content)

async def load_logs_async():
    log_content = ""
    log_dir = PATHS["data"]
    if Path(log_dir).exists() and Path(log_dir).is_dir():
        for log_file in sorted(Path(log_dir).glob("*.log")):  # Only .log files, sorted
            async with aiofiles.open(log_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                log_content += f"Log File [{log_file.name}]:\n{content}\n"
    else:
        print(f"--> WARNING: Log directory '{log_dir}' not found.")
    return log_content

# Async function to read user input JSON
async def load_user_input_async():
    async with aiofiles.open(PATHS["user_input"], 'r', encoding='utf-8') as f:
        user_question = await f.read()
    if not user_question.strip():
        raise ValueError("User input file is empty. Please provide a valid JSON, TXT, or MD file.")
    return json.loads(user_question.strip())


async def load_template_async():
    async with aiofiles.open(PATHS["prompt"], 'r', encoding='utf-8') as f:
        raw_template_string = await f.read()
    prompt_template = PromptTemplate.from_template(raw_template_string)
    return prompt_template

# Async function to save response to a file
async def save_response_to_file_async(filepath, output_list):
    async with aiofiles.open(filepath, 'w', encoding='utf-8') as output_file:
        for ele in output_list:
            await output_file.write(ele + "\n")

def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    cleaned = re.sub(r'\n\s*\n', '\n\n', text)
    cleaned = cleaned.encode("ascii", "ignore").decode("ascii")
    return cleaned.strip()

def read_system_from_modelfile(modelfile_path):
    with open(modelfile_path, "r", encoding="utf-8") as f:
        content = f.read()
        match = re.search(r'SYSTEM\s+"""(.*?)"""', content, re.DOTALL)
        if match:
            return match.group(1).strip()
    return ""

# Main async function
async def main(args, config_data, paths, model_config):
    # --- CONFIGURATION ---
    config_data = await load_toml_async()
    if args.model not in model_config:
        raise ValueError(f"Language model '{args.model}' is not available.")

    embedding_model = config_data[args.env]["embedding_models"][0]
    language_model = model_config[args.model]["config"]
    hostname = config_data["database"]["ollama"]
    CONNECTION_STRING = config_data["settings"]["connection_string"]
    COLLECTION_NAME = config_data["settings"]["collection_name"]

    # --- INITIALIZATION ---
    try:
        embeddings = OllamaEmbeddings(base_url=hostname, model=embedding_model)
        db = PGVector(
            embedding_function=embeddings,
            collection_name=COLLECTION_NAME,
            connection_string=CONNECTION_STRING,
            use_jsonb=True,
        )
        client = ollama.Client(host=hostname)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize LangChain/Ollama components: {e}")

    # --- LOAD USER INPUT ---
    # We only need to load the user's questions, not the template file.
    user_questions = await load_user_input_async() # Assuming this loads a list of dicts
    
    output_list = []

    # --- MAIN PROCESSING LOOP ---
    for query_obj in user_questions:
        question = query_obj.get("question", "").strip()
        log_filename = query_obj.get("log_file", "").strip()

        if not question:
            continue # Skip empty questions

        print("\n" + "🔍 QUERY".center(100, "="))
        print(fill(question, width=100))

        # 1. Read the specific log file for this query
        log_content = ""
        if log_filename:
            log_path = Path(paths["data"]) / log_filename
            print(f"\n--> Processing log file: {log_path}")
            try:
                async with aiofiles.open(log_path, 'r', encoding='utf-8') as f:
                    log_content = await f.read()
            except FileNotFoundError:
                print(f"--> WARNING: Specified log file '{log_path}' not found.")


        # Improved error extraction: match more error types and fallback to log head if no error found
        error_lines = re.findall(
            r"^(?:Traceback.*|.*(?:ERROR|Exception|TypeError|RuntimeError|ValueError|failed|fatal|cannot|CRITICAL|AssertionError|ModuleNotFoundError|ImportError|IndexError|KeyError|AttributeError|NameError|OSError|IOError|ZeroDivisionError|TimeoutError|PermissionError|FileNotFoundError).*)$",
            log_content,
            re.MULTILINE | re.IGNORECASE
        )
        error_summary = "\n".join(error_lines).strip()
        # Fallback: if no error lines, include first 10 lines of log
        if not error_summary and log_content:
            log_head = "\n".join(log_content.splitlines()[:10])
            error_summary = f"[No error lines found. Log head:]\n{log_head}"

        # 2. Retrieve relevant documents
        enriched_query = f"{question}\n\nKey Error from Log:\n{error_summary}"
        results = db.similarity_search_with_score(enriched_query, k=5)
        # Print top retrieved doc scores for debugging
        print("Top retrieved document scores:")
        for i, (doc, score) in enumerate(results[:3], 1):
            print(f"  Doc #{i}: Score={score:.4f}")

        # Using the top 3 results for context
        retrieved_contexts = [doc.page_content for doc, score in results[:3]]

        # 3. Augment: Combine the evidence and the knowledge
        log_section = f"Log Content:\n{error_summary}" if error_summary else "Log Content: [None provided]"
        docs_section = f"Retrieved Documentation:\n" + "\n---\n".join(retrieved_contexts) if retrieved_contexts else "Retrieved Documentation: [None found]"
        # This is the content that will go into the {{ .Prompt }} variable of your Modelfile's template.
        prompt_content_for_llm = f"{log_section}\n\n{docs_section}\n\nQuestion: {question}"

        # 4. Generate the answer
        try:
            # The 'prompt' here is the raw content. The template is handled by the custom model on the server.
            response = client.generate(
                model=language_model, 
                prompt=prompt_content_for_llm, 
                options={"temperature": 0.2}
            )
            response_text = response.get('response', '').strip()
        except Exception as e:
            response_text = f"Error generating response: {e}"

        # --- Display & Save Results ---
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
    await save_response_to_file_async(paths["output"], output_list)
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
        embeddings = OllamaEmbeddings(base_url=hostname, model=embedding_model)
        db = PGVector(embedding_function=embeddings, collection_name=COLLECTION_NAME, connection_string=CONNECTION_STRING, use_jsonb=True)

        with open(paths["eval_data"], 'r', encoding='utf-8') as f:
            eval_data = json.load(f)

        async with aiofiles.open(paths["prompt"], 'r', encoding='utf-8') as f:
            raw_template_string = await f.read()
            
        prompt_template = PromptTemplate.from_template(raw_template_string)
        client = ollama.Client(host=hostname)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize for evaluation: {e}")

    questions_list, ground_truths_list, contexts_list, predictions_list = [], [], [], []

    for item in eval_data:
        question = item["question"]
        ground_truth = item["ground_truth"]
        log_excerpt = item.get("log_excerpt", "")
        # Mirror main pipeline: enrich query with log excerpt
        enriched_query = f"{question}\n\nKey Error from Log:\n{log_excerpt}"
        results_with_scores = db.similarity_search_with_relevance_scores(enriched_query, k=10)
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

    # --- Final RAGAS Evaluation ---
    print("\n--- Aggregating results for Ragas Evaluation ---")
    ragas_dataset = Dataset.from_dict({
        "question": questions_list,
        "answer": predictions_list,
        "contexts": contexts_list,
        "ground_truth": ground_truths_list,
    })
    
    try:
        # Increase timeout for OllamaLLM used in RAGAS
        ollama_llm_for_ragas = OllamaLLM(base_url=hostname, model=language_model, timeout=900)
        llm_wrapper = LangchainLLMWrapper(ollama_llm_for_ragas)
        metrics = [answer_relevancy, faithfulness, context_precision, context_recall]
        ragas_results = evaluate(ragas_dataset, metrics=metrics, llm=llm_wrapper, embeddings=embeddings)
        print("\n--- FINAL RAGAS EVALUATION SCORES ---")
        print(ragas_results)
    except Exception as e:
        print(f"Ragas evaluation failed: {e}")


# New async function to process a single query from API
async def process_query(
    log_content: str,
    user_question: str, # FIX: Changed parameter name from 'query' to match what the server is likely using.
    config: dict,
    model_name: str,
    embedding_model: str,
    top_k: int = 3
) -> Tuple[str, list]:
    """
    Process a single query using provided log content and user question
    passed as direct keyword arguments.
    """
    # --- Configuration ---
    connection_string = config["settings"]["connection_string"]
    collection_name = config["settings"]["collection_name"]
    hostname = config["database"]["ollama"]

    # --- Initialization ---
    try:
        embeddings = OllamaEmbeddings(base_url=hostname, model=embedding_model)
        db = PGVector(
            embedding_function=embeddings,
            collection_name=collection_name,
            connection_string=connection_string,
            use_jsonb=True,
        )
        client = ollama.Client(host=hostname)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize embeddings or database: {e}")

    # --- 1. Enrich the Query with Evidence from the Log ---
    # Add more error keywords for broader error extraction
    error_lines = re.findall(
        r"^(?:Traceback.*|.*(?:ERROR|Exception|TypeError|RuntimeError|ValueError|failed|fatal|cannot|CRITICAL|AssertionError|ModuleNotFoundError|ImportError|IndexError|KeyError|AttributeError|NameError|OSError|IOError|ZeroDivisionError|TimeoutError|PermissionError|FileNotFoundError).*)$",
        log_content,
        re.MULTILINE | re.IGNORECASE
    )
    error_summary = "\n".join(error_lines).strip()
    enriched_query = f"{user_question}\n\nKey Error from Log:\n{error_summary}"

    # --- 2. Retrieve Relevant Documents ---
    results = db.similarity_search_with_score(enriched_query, k=top_k)
    
    related_documents_for_response = [
        {"score": score, "content": doc.page_content} for doc, score in results
    ]

    # --- 3. Augment the Prompt ---
    retrieved_contexts = [doc.page_content for doc, score in results]
    log_section = f"Log Content:\n{error_summary}" if error_summary else "Log Content: [None provided]"
    docs_section = f"Retrieved Documentation:\n" + "\n---\n".join(retrieved_contexts) if retrieved_contexts else "Retrieved Documentation: [None found]"
    
    prompt_content_for_llm = f"{log_section}\n\n{docs_section}\n\nQuestion: {user_question}"

    # --- 4. Generate the Answer ---
    response_text = ""
    try:
        response = client.generate(
            model=model_name,
            prompt=prompt_content_for_llm,
            options={"temperature": 0.2},
        )
        response_text = response.get('response', '').strip()
    except Exception as e:
        response_text = f"An error occurred while processing your request: {e}"

    # Return the final text and the structured documents for the client.
    return response_text, related_documents_for_response


# Run the main async function
if __name__ == "__main__":
    try:
        if args.evaluate:
            config_data_sync = asyncio.run(load_toml_async())
            asyncio.run(run_evaluation(args, config_data=config_data_sync, paths=PATHS, model_config=model_config))
        else:
            config_data_sync = asyncio.run(load_toml_async())
            asyncio.run(main(args, config_data=config_data_sync, paths=PATHS, model_config=model_config))
    except Exception as e:
        print(f"An unexpected error occurred in main: {e}", file=sys.stderr)
        sys.exit(1)
