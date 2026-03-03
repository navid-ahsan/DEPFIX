#!/bin/bash
echo "Starting to build a networking please wait..."

# Create a Docker network
docker network create -d bridge rag-net

echo "Starting to build a containers please wait..."

# Pull the image of pgvector
docker pull ankane/pgvector:latest
# Create a container for pgvector
docker run --cpus all --name pgvector \
  --network rag-net \
  -p 5432:5432 \
  -e POSTGRES_PASSWORD=root \
  -e POSTGRES_DB=vector_db \
  -d ankane/pgvector 

echo "pgvector container created..."

docker start pgvector

mkdir -p app/data/models
# Pull the image of ollama
docker pull ollama/ollama:latest
# Create a container for ollama
docker run --gpus all --name ollama \
  --network rag-net \
  -p 11434:11434 \
  -v /home/navid/app/project_rag/data/models:/root/.ollama/models \
  -v /home/navid/app/project_rag/ollama_build:/root/.ollama/build \
  -d ollama/ollama 

echo "ollama container created..."

docker exec -it ollama bash -c "ollama pull mxbai-embed-large"
docker exec -it ollama bash -c "ollama pull gemma3:27b"
docker exec -it ollama bash -c "ollama pull llama4"
docker exec -it ollama bash -c "ollama create dgx_gemma3 -f /root/.ollama/build/dgx_model/gemma3/Modelfile"
docker exec -it ollama bash -c "ollama create dgx_llama4 -f /root/.ollama/build/dgx_model/llama4/Modelfile"

docker start ollama

# Pull the image of python script Dockerfile
docker build -t rag-image -f /home/navid/app/project_rag/Dockerfile .
# Create a container for the Python script
docker run --name py-script \
  --network rag-net \
  -p 8000:8000 \
  -v /home/navid/app/project_rag:/app \
  -it rag-image

# Ensure the container is running before connecting it to the network
docker start py-script

echo "RAG-script container created..."

echo "Connectig all containers to the same network..."


# Add the containers to the same network
docker network connect rag-net pgvector
docker network connect rag-net ollama 
docker network connect rag-net py-script

echo "All containers are running and connected to the same network..."
echo "Goodbye!"


