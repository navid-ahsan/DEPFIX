#!/usr/bin/env python3
"""
RAGAS Evaluation Script — compatible with RAGAS v0.2.x

Root causes fixed vs the legacy rag_app.py --evaluate mode:
  1. Uses EvaluationDataset + SingleTurnSample (v0.2.x schema,
     field names: user_input / response / retrieved_contexts / reference).
     The old Dataset.from_dict() with 'question/answer/contexts/ground_truth'
     no longer maps to the metric schema, producing silent NaN results.
  2. Removes the hard DISTANCE_THRESHOLD = 0.3 filter.
     similarity_search_with_relevance_scores returns L2 distances;
     the threshold was so tight that 0–1 docs passed per query,
     making context_precision / context_recall / faithfulness all NaN.
  3. Wraps both the LLM and the embeddings in RAGAS-native wrappers
     (LangchainLLMWrapper, LangchainEmbeddingsWrapper).
  4. Uses RunConfig(timeout=900) so local Ollama calls are not killed early.
  5. Saves scores to data/outputs/eval_results.json for run_evaluation.sh.

Usage:
    python scripts/run_ragas_eval.py \\
        --env lab_model \\
        --model mistral:7b \\
        --top-k 5
"""

import os
import sys
import json
import toml
import argparse
import traceback
from pathlib import Path

# ── RAGAS v0.2.x ────────────────────────────────────────────────────────────
from ragas import evaluate
from ragas.dataset_schema import EvaluationDataset, SingleTurnSample
from ragas.metrics import answer_relevancy, faithfulness, context_precision, context_recall
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.run_config import RunConfig

# ── LangChain / Ollama ───────────────────────────────────────────────────────
from langchain_community.vectorstores.pgvector import PGVector
from langchain_ollama import OllamaEmbeddings, OllamaLLM

# ── CLI ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Run RAGAS evaluation on the RAG pipeline.")
parser.add_argument("--config",    default="ollama_build/config.toml",
                    help="Path to the TOML config file")
parser.add_argument("--eval-data", default="data/eval_dataset.json",
                    help="Path to the JSON evaluation dataset")
parser.add_argument("--env",       default="lab_model",
                    choices=["lab_model", "dgx_model"])
parser.add_argument("--model",     default="mistral:7b",
                    help="Ollama model tag to use for generation and RAGAS judging")
parser.add_argument("--output",    default="data/outputs/eval_results.json",
                    help="Where to write the final RAGAS scores (JSON)")
parser.add_argument("--top-k",     type=int, default=5,
                    help="Number of docs to retrieve per query (no hard threshold)")
args = parser.parse_args()

# ── CONFIG ───────────────────────────────────────────────────────────────────
config_path = Path(args.config)
if not config_path.exists():
    print(f"ERROR: Config not found at {config_path}", file=sys.stderr)
    sys.exit(1)

config = toml.load(config_path)
embedding_model    = config[args.env]["embedding_models"][0]
hostname           = os.getenv("OLLAMA_HOST") or config["database"]["ollama"]
connection_string  = os.getenv("DATABASE_URL") or config["settings"]["connection_string"]
collection_name    = config["settings"]["collection_name"]

print(f"  ollama    : {hostname}")
print(f"  model     : {args.model}")
print(f"  embed     : {embedding_model}")
print(f"  pgvector  : {collection_name}")
print(f"  top-k     : {args.top_k}")

# ── LOAD EVAL DATASET ────────────────────────────────────────────────────────
eval_path = Path(args.eval_data)
if not eval_path.exists():
    print(f"ERROR: Eval dataset not found at {eval_path}", file=sys.stderr)
    sys.exit(1)

with open(eval_path, encoding="utf-8") as f:
    eval_data = json.load(f)

print(f"\nLoaded {len(eval_data)} evaluation cases from {eval_path}\n")

# ── INIT VECTOR DB ───────────────────────────────────────────────────────────
try:
    embeddings = OllamaEmbeddings(base_url=hostname, model=embedding_model)
    db = PGVector(
        embedding_function=embeddings,
        collection_name=collection_name,
        connection_string=connection_string,
        use_jsonb=True,
    )
    print("Connected to pgvector.")
except Exception as exc:
    print(f"ERROR: Failed to connect to pgvector: {exc}", file=sys.stderr)
    sys.exit(1)

# ── INIT GENERATION LLM ──────────────────────────────────────────────────────
try:
    gen_llm = OllamaLLM(base_url=hostname, model=args.model, timeout=300)
    print(f"Generation LLM ready: {args.model}\n")
except Exception as exc:
    print(f"ERROR: Failed to initialise Ollama: {exc}", file=sys.stderr)
    sys.exit(1)

# ── RETRIEVAL + GENERATION LOOP ──────────────────────────────────────────────
ANSWER_PROMPT = (
    "You are a CI/CD error analysis assistant. Using ONLY the provided "
    "documentation context, identify the root cause of the error and give "
    "a specific, actionable fix.\n\n"
    "CONTEXT:\n{context}\n\n"
    "QUESTION: {question}\n\n"
    "ERROR LOG EXCERPT:\n{log_excerpt}\n\n"
    "ANSWER:"
)

samples: list[SingleTurnSample] = []
failed_generations = 0

for idx, item in enumerate(eval_data):
    question    = item["question"]
    ground_truth = item["ground_truth"]
    log_excerpt  = item.get("log_excerpt", "")

    print(f"[{idx+1:02d}/{len(eval_data)}] {question[:72]}...")

    # ── Retrieval (no hard distance filter — let top-k do the work) ──────────
    enriched_query = f"{question}\n\nError excerpt:\n{log_excerpt}" if log_excerpt else question
    try:
        raw_docs = db.similarity_search(enriched_query, k=args.top_k)
        retrieved_contexts = [doc.page_content for doc in raw_docs]
        print(f"           retrieved {len(retrieved_contexts)} docs")
    except Exception as exc:
        print(f"           WARNING — retrieval failed: {exc}")
        retrieved_contexts = []

    context_string = "\n---\n".join(retrieved_contexts) if retrieved_contexts \
                     else "(No relevant documentation retrieved.)"

    # ── Generation ────────────────────────────────────────────────────────────
    prompt = ANSWER_PROMPT.format(
        context=context_string,
        question=question,
        log_excerpt=log_excerpt,
    )
    try:
        response_text = gen_llm.invoke(prompt)
        if not isinstance(response_text, str):
            response_text = str(response_text)
        response_text = response_text.strip()
        print(f"           generated  {len(response_text)} chars")
    except Exception as exc:
        print(f"           WARNING — generation failed: {exc}")
        response_text = "Unable to generate response."
        failed_generations += 1

    samples.append(SingleTurnSample(
        user_input=question,
        response=response_text,
        retrieved_contexts=retrieved_contexts,
        reference=ground_truth,
    ))

print(f"\nProcessed {len(samples)} samples  ({failed_generations} generation failures)\n")

if not samples:
    print("ERROR: No samples to evaluate.", file=sys.stderr)
    sys.exit(1)

# ── RAGAS EVALUATION ─────────────────────────────────────────────────────────
print("Starting RAGAS evaluation — this may take 10–40 minutes with a local LLM…\n")

dataset = EvaluationDataset(samples=samples)

ragas_llm  = LangchainLLMWrapper(
    OllamaLLM(base_url=hostname, model=args.model, timeout=900)
)
ragas_emb  = LangchainEmbeddingsWrapper(embeddings)
run_config = RunConfig(timeout=900, max_retries=2, max_wait=120)

try:
    results = evaluate(
        dataset=dataset,
        metrics=[answer_relevancy, faithfulness, context_precision, context_recall],
        llm=ragas_llm,
        embeddings=ragas_emb,
        run_config=run_config,
        raise_exceptions=False,   # log NaN entries but don't crash
        show_progress=True,
    )

    print("\n" + "=" * 60)
    print("RAGAS EVALUATION RESULTS")
    print("=" * 60)

    scores: dict = {}
    for metric_name, value in results.items():
        if isinstance(value, float):
            tag = "⚠ NaN" if value != value else f"{value:.4f}"  # NaN check
            print(f"  {metric_name:<30s}: {tag}")
            scores[metric_name] = None if value != value else round(value, 4)
        else:
            scores[metric_name] = value
            print(f"  {metric_name:<30s}: {value}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_data = {
        "scores": scores,
        "config": {
            "model":               args.model,
            "embedding_model":     embedding_model,
            "env":                 args.env,
            "top_k":               args.top_k,
            "n_eval_cases":        len(samples),
            "n_failed_generations": failed_generations,
        },
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    print(f"\nSaved to {output_path}")

except Exception as exc:
    print(f"\nERROR: RAGAS evaluation failed: {exc}", file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)
