#!/bin/bash
# RAG Evaluation Runner Script
# Runs RAGAS evaluation on the evaluation dataset
# Usage: bash scripts/run_evaluation.sh [env] [model]

set -e

# Default values
ENV=${1:-lab_model}
MODEL=${2:-mistral:7b}
EVAL_DATASET_PATH="archive/legacy_src/eval_dataset.json"
OUTPUT_DIR="data/outputs"

echo "========================================"
echo "RAG Evaluation Script"
echo "========================================"
echo ""
echo "Environment: $ENV"
echo "Model: $MODEL"
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

# Run the evaluation using rag_app.py with --evaluate flag
python3 src/rag_app.py --env "$ENV" --model "$MODEL" --evaluate

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
