import json
from pathlib import Path

# --- CONFIG ---
EVAL_DATASET_PATH = Path(__file__).parent / "eval_dataset.json"
OUTPUT_PATH = Path(__file__).parent.parent / "data" / "documents" / "eval_cases.jsonl"

# --- LOAD EVAL DATASET ---
with open(EVAL_DATASET_PATH, "r", encoding="utf-8") as f:
    eval_data = json.load(f)

# --- CONVERT TO DOCUMENT FORMAT ---
# Each eval case becomes a document with content = log_excerpt + ground_truth
# and metadata for traceability

documents = []
for idx, item in enumerate(eval_data):
    doc = {
        "library": "eval_case",
        "source": f"eval_dataset.json#{idx}",
        "content": f"Log Excerpt:\n{item.get('log_excerpt', '').strip()}\n\nGround Truth:\n{item.get('ground_truth', '').strip()}\n\nQuestion:\n{item.get('question', '').strip()}"
    }
    documents.append(doc)

# --- WRITE TO JSONL ---
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    for doc in documents:
        json.dump(doc, f, ensure_ascii=False)
        f.write("\n")

print(f"Wrote {len(documents)} eval cases to {OUTPUT_PATH}")
