#!/bin/bash
set -e

eval "$(conda shell.bash hook)"
conda activate biomni_e1

cd /app

# Wait for Redis
REDIS_URL="${REDIS_URL:-redis://redis:6379/0}"
REDIS_HOST=$(echo "$REDIS_URL" | sed -n 's|.*://\([^:/]*\).*|\1|p')
REDIS_PORT=$(echo "$REDIS_URL" | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
REDIS_PORT="${REDIS_PORT:-6379}"

echo "Waiting for Redis at ${REDIS_HOST}:${REDIS_PORT}..."
until python -c "import socket; s=socket.create_connection(('$REDIS_HOST', $REDIS_PORT), timeout=2); s.close()" 2>/dev/null; do
    sleep 2
done
echo "Redis is ready."

# Wait for PostgreSQL
DATABASE_URL="${DATABASE_URL:-}"
if [ -n "$DATABASE_URL" ]; then
    PG_HOST=$(echo "$DATABASE_URL" | sed -n 's|.*@\([^:/]*\).*|\1|p')
    PG_PORT=$(echo "$DATABASE_URL" | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
    PG_PORT="${PG_PORT:-5432}"

    echo "Waiting for PostgreSQL at ${PG_HOST}:${PG_PORT}..."
    until python -c "import socket; s=socket.create_connection(('$PG_HOST', $PG_PORT), timeout=2); s.close()" 2>/dev/null; do
        sleep 2
    done
    echo "PostgreSQL is ready."
fi

# Ensure workspace directory exists
mkdir -p "${WORKSPACE_BASE_PATH:-/data/workspaces}"

echo "Starting Celery worker..."
exec celery -A backend.app.celery_app worker \
    --queues=code \
    --concurrency="${CELERY_CONCURRENCY:-2}" \
    --loglevel=info \
    --hostname="worker@%h"
