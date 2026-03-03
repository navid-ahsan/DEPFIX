#!/bin/bash

echo "Starting to build a Docker network, please wait..."

# Variables
NETWORK_NAME="rag-net"
PGVECTOR_IMAGE="ankane/pgvector:latest"
OLLAMA_IMAGE="ollama/ollama:latest"
PY_IMAGE="rag-image"
PROJECT_ROOT="$(pwd)"
MODELFILE="$PROJECT_ROOT/ollama_build/dgx_model/Modelfile"
PY_DOCKERFILE="$PROJECT_ROOT/Dockerfile"
MODEL_DIR="$PROJECT_ROOT/data/models"
BUILD_DIR="$PROJECT_ROOT/ollama_build"
CPUS="8"
MEMORY="64g"
GPU_DEVICES_ARRAY="0"

# Create Docker network
docker network create -d bridge $NETWORK_NAME

echo "Building containers, please wait..."

# Start pgvector
docker pull $PGVECTOR_IMAGE
docker run --cpus all --name pgvector \
  --network $NETWORK_NAME \
  -p 5432:5432 \
  -e POSTGRES_PASSWORD=root \
  -e POSTGRES_DB=vector_db \
  --cpus="$CPUS" --memory="$MEMORY" \
  -d $PGVECTOR_IMAGE

echo "pgvector container created..."

# Start ollama
docker pull $OLLAMA_IMAGE
docker run --gpus all --name ollama \
  --network $NETWORK_NAME \
  -p 11434:11434 \
  mkdir -p $MODEL_DIR \
  -v $BUILD_DIR:/root/.ollama/build \
  --cpus="$CPUS" --memory="$MEMORY" \
  -d -it $OLLAMA_IMAGE

echo "ollama container created..."

# Pull models and build custom model in Ollama
docker exec -it ollama bash -c "ollama pull mxbai-embed-large"
docker exec -it ollama bash -c "ollama pull gemma3:27b"
docker exec -it ollama bash -c "ollama create dgx_gemma3 -f /root/.ollama/build/dgx_model/Modelfile"

# Start Python app container
docker build -t $PY_IMAGE -f $PY_DOCKERFILE $PROJECT_ROOT
docker run --name py-script \
  --network $NETWORK_NAME \
  -p 8000:8000 \
  -v $PROJECT_ROOT:/app \
  --cpus="$CPUS" --memory="$MEMORY" \
  -it $PY_IMAGE

echo "py-script container created..."

# Ensure containers are running before connecting to the network
docker start pgvector
docker start ollama
docker start py-script


echo "Connecting all containers to the same network..."
echo "All containers are running and connected to the same network."
echo "Goodbye!"