#!/bin/bash
set -e

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <environment> <model_tag> <model_dir>"
    exit 1
fi

ARG_ENV="$1"
ARG_MODEL_TAG="$2"
ARG_MODEL_DIR="$3"

OLLAMA_MODELDIR_PATH="/root/.ollama/build/$ARG_ENV/$ARG_MODEL_DIR"
OLLAMA_MODEFILE_PATH="${OLLAMA_MODELDIR_PATH}/Modelfile"

# Check Modelfile exists inside ollama container
docker exec ollama test -f "$OLLAMA_MODEFILE_PATH"
if [ $? -ne 0 ]; then
    echo "ERROR: Modelfile does not exist at $OLLAMA_MODEFILE_PATH inside ollama container"
    exit 1
fi

echo "--- Step 1: Found Modelfile in ollama container at $OLLAMA_MODEFILE_PATH ---"
echo ""

# Step 2: Build the model inside ollama container
docker exec ollama ollama create "$ARG_MODEL_TAG" -f "$OLLAMA_MODEFILE_PATH"

# Step 3: Run your RAG app in py-script container
docker-compose exec py-script python3 /app/src/rag_app.py --env "$ARG_ENV" --model "$ARG_MODEL_TAG" --build-model