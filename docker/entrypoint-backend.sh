#!/bin/bash
set -e

eval "$(conda shell.bash hook)"
conda activate biomni_e1

cd /app

# Wait for Ollama
OLLAMA_URL="${OLLAMA_BASE_URL:-http://ollama:11434}"
BIOMNI_SOURCE="${BIOMNI_SOURCE:-Ollama}"

if [ "$BIOMNI_SOURCE" = "Ollama" ]; then
    echo "Waiting for Ollama at ${OLLAMA_URL}..."
    until curl -sf "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; do
        sleep 2
    done
    echo "Ollama is ready."
fi

# Wait for PostgreSQL
DATABASE_URL="${DATABASE_URL:-}"
if [ -n "$DATABASE_URL" ]; then
    echo "Waiting for PostgreSQL..."
    # Extract host:port from database URL
    PG_HOST=$(echo "$DATABASE_URL" | sed -n 's|.*@\([^:/]*\).*|\1|p')
    PG_PORT=$(echo "$DATABASE_URL" | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
    PG_PORT="${PG_PORT:-5432}"
    until python -c "import socket; s=socket.create_connection(('$PG_HOST', $PG_PORT), timeout=2); s.close()" 2>/dev/null; do
        sleep 2
    done
    echo "PostgreSQL is ready."

    # Run migrations
    echo "Running database migrations..."
    cd /app/backend && alembic upgrade head
    cd /app
fi

echo "Starting orenoBiomni backend..."
exec uvicorn backend.app.main:app \
    --host "${API_HOST:-0.0.0.0}" \
    --port "${API_PORT:-8000}" \
    --workers 1
