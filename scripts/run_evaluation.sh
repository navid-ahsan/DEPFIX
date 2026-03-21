#!/bin/bash
# RAG Evaluation Runner Script
# Runs RAGAS evaluation on the evaluation dataset
# Usage: bash scripts/run_evaluation.sh [env] [model]

set -e

# Default values
ENV=${1:-lab_model}
MODEL=${2:-mistral:7b}
EVAL_DATASET_PATH="data/eval_dataset.json"   # 25-case dataset aligned to real log errors
OUTPUT_DIR="data/outputs"

echo "========================================"
echo "RAG Evaluation Script  (RAGAS v0.2.x)"
echo "========================================"
echo ""
echo "Environment      : $ENV"
echo "Model            : $MODEL"
echo "Evaluation Dataset: $EVAL_DATASET_PATH"
echo ""

# Check if evaluation dataset exists
if [ ! -f "$EVAL_DATASET_PATH" ]; then
    echo "❌ ERROR: Evaluation dataset not found at $EVAL_DATASET_PATH"
    exit 1
fi

# Check if output directory exists
if [ ! -d "$OUTPUT_DIR" ]; then
    echo "Creating output directory: $OUTPUT_DIR"
    mkdir -p "$OUTPUT_DIR"
fi

echo "Starting RAG evaluation..."
echo ""

# Use the fixed RAGAS v0.2.x evaluation script (scripts/run_ragas_eval.py).
# Key improvements over the legacy rag_app.py --evaluate mode:
#   • EvaluationDataset + SingleTurnSample (v0.2.x field schema)
#   • No hard distance threshold — retrieves top-k=5 without filtering
#   • RunConfig(timeout=900) for local Ollama calls
#   • Saves data/outputs/eval_results.json with per-metric scores
python3 scripts/run_ragas_eval.py \
    --env   "$ENV" \
    --model "$MODEL" \
    --eval-data "$EVAL_DATASET_PATH" \
    --output "$OUTPUT_DIR/eval_results.json"

EVAL_RESULT=$?

echo ""
echo "========================================"
if [ $EVAL_RESULT -eq 0 ]; then
    echo "✅ Evaluation completed successfully!"
    echo ""
    echo "Evaluation results saved to: $OUTPUT_DIR/"

    # Display evaluation metrics if available
    if [ -f "$OUTPUT_DIR/eval_results.json" ]; then
        echo ""
        echo "Evaluation Metrics:"
        python3 -c "
import json
try:
    with open('$OUTPUT_DIR/eval_results.json', 'r') as f:
        results = json.load(f)
        for metric, value in results.items():
            if isinstance(value, float):
                print(f'  • {metric}: {value:.4f}')
            else:
                print(f'  • {metric}: {value}')
except Exception as e:
    print(f'  (Could not parse results: {e})')
"
    fi
else
    echo "❌ Evaluation failed with exit code $EVAL_RESULT"
fi
echo "========================================"

exit $EVAL_RESULT
