#!/bin/bash

# Create network
docker network create rag-net 2>/dev/null || true

echo "Starting Ollama..."
docker run -d \
  --name ollama \
  --network rag-net \
  -p 11434:11434 \
  -v ollama_data:/root/.ollama \
  -e OLLAMA_HOST=0.0.0.0:11434 \
  ollama/ollama:latest

sleep 5

echo "Starting pgvector..."
docker run -d \
  --name pgvector \
  --network rag-net \
  -p 5432:5432 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password123 \
  -e POSTGRES_DB=vector_db \
  -v pgvector_data:/var/lib/postgresql/data \
  ankane/pgvector:latest

sleep 10

echo "Starting Backend..."
docker run -d \
  --name rag-backend \
  --network rag-net \
  -p 8000:8000 \
  -e PYTHONUNBUFFERED=1 \
  -e DATABASE_URL=postgresql+psycopg2://postgres:password123@pgvector:5432/vector_db \
  -e OLLAMA_HOST=http://ollama:11434 \
  -e ENVIRONMENT=docker \
  -v /home/navid/project/socialwork/backend:/app/backend \
  -v /home/navid/project/socialwork/data:/app/data \
  -w /app \
  python:3.12 \
  bash -c "pip install -q -r /app/backend/../requirements.txt && python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"

sleep 10

echo "Starting Frontend..."
docker run -d \
  --name rag-frontend \
  --network rag-net \
  -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://backend:8000 \
  -e NODE_ENV=production \
  -w /app \
  node:20-alpine \
  bash -c "npm ci --omit=dev && npm start"

sleep 5

echo ""
echo "========================================="
echo "✅ Docker Containers Started Successfully!"
echo "========================================="
echo ""
echo "Services Running:"
echo "  📡 Ollama:    http://localhost:11434"
echo "  🗄️  pgvector:  localhost:5432"  
echo "  🔙 Backend:   http://localhost:8000"
echo "  🎨 Frontend:  http://localhost:3000"
echo ""
echo "All services on network: rag-net"
echo ""
echo "Open: http://localhost:3000/dashboard"
