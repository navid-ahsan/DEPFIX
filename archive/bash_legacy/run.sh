#!/bin/bash

set -e

echo "Starting to build a Docker containers, please wait..."

# Check if Docker is running
services=("ollama" "pgvector" "py-script")

for service in "${services[@]}"; do
    if ! docker ps --format '{{.Names}}' | grep -q "^${service}$"; then
        docker-compose up -d "${service}"
    fi
done

echo "All services are up and running."

# Running request.py script
docker-compose exec py-script python3 /app/src/request.py