#!/bin/bash

echo "Starting to build a Docker network, please wait..."

# Variables
NETWORK_NAME="rag-net"
PGVECTOR_IMAGE="ankane/pgvector:latest"
OLLAMA_IMAGE="ollama/ollama:latest"
PY_IMAGE="rag-image"
PROJECT_ROOT="$(pwd)"
PY_DOCKERFILE="$PROJECT_ROOT/Dockerfile"
MODEL_DIR="$PROJECT_ROOT/data/models"
BUILD_DIR="$PROJECT_ROOT/ollama_build"
# Performing resource allocation
# Note: Adjust these values based on your system's capabilities
CPUS="8"
MEMORY="64g"
GPU_DEVICES_ARRAY="0"

# Container settings
CONTAINER_NAMES=("pgvector" "ollama" "py-script")
IMAGES=("$PGVECTOR_IMAGE" "$OLLAMA_IMAGE" "$PY_IMAGE")
PORTS=("5432:5432" "11434:11434" "8000:8000")
EXTRA_ARGS=(
  "-e POSTGRES_PASSWORD=root -e POSTGRES_DB=vector_db"
  "-v $MODEL_DIR:/root/.ollama/models -v $BUILD_DIR:/root/.ollama/build"
  "-v $PROJECT_ROOT:/app --network $NETWORK_NAME"
)

# Create Docker network
docker network create -d bridge $NETWORK_NAME

echo "Building containers, please wait..."

# Pull/build images
docker pull $PGVECTOR_IMAGE
docker pull $OLLAMA_IMAGE
docker build -t $PY_IMAGE -f $PY_DOCKERFILE $PROJECT_ROOT

# Run containers in a loop
for i in "${!CONTAINER_NAMES[@]}"; do
  NAME="${CONTAINER_NAMES[$i]}"
  IMAGE="${IMAGES[$i]}"
  PORT="${PORTS[$i]}"
  ARGS="${EXTRA_ARGS[$i]}"

  # Remove existing container if exists
  docker rm -f "$NAME" 2>/dev/null

  # Run container
  if [[ "$NAME" == "pgvector" ]]; then
    docker run --cpus="$CPUS" --memory="$MEMORY" --name "$NAME" -p $PORT $ARGS -d $IMAGE
  elif [[ "$NAME" == "ollama" ]]; then
    docker run --gpus "$GPU_DEVICES_ARRAY" --cpus="$CPUS" --memory="$MEMORY" --name "$NAME" -p $PORT $ARGS -d -it $IMAGE
  else
    docker run --cpus="$CPUS" --memory="$MEMORY" --name "$NAME" -p $PORT $ARGS -it $IMAGE
  fi

  # Connect to network (if not already)
  docker network connect $NETWORK_NAME "$NAME" 2>/dev/null

  echo "$NAME container created and connected to $NETWORK_NAME."
done

echo "All containers are running and connected to the same network."
echo "Goodbye!"