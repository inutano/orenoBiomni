#!/bin/bash
# PostgreSQL backup for orenoBiomni
#
# Usage:
#   ./scripts/backup-db.sh                    # backup to ./backups/
#   ./scripts/backup-db.sh /path/to/dir       # backup to custom directory
#   KEEP_DAYS=30 ./scripts/backup-db.sh       # keep backups for 30 days (default: 7)
#
# Restore:
#   gunzip -c backups/orenoiomni_2026-03-20_120000.sql.gz | \
#     docker compose exec -T postgres psql -U ${POSTGRES_USER:-biomni} orenoiomni
set -euo pipefail

BACKUP_DIR="${1:-./backups}"
KEEP_DAYS="${KEEP_DAYS:-7}"
TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)
FILENAME="orenoiomni_${TIMESTAMP}.sql.gz"

# Load .env if present
if [ -f .env ]; then
    set -a; source .env; set +a
fi

PG_USER="${POSTGRES_USER:-biomni}"
PG_DB="orenoiomni"

mkdir -p "$BACKUP_DIR"

echo "Backing up database to ${BACKUP_DIR}/${FILENAME}..."
docker compose exec -T postgres pg_dump \
    -U "$PG_USER" \
    --format=plain \
    --no-owner \
    "$PG_DB" | gzip > "${BACKUP_DIR}/${FILENAME}"

SIZE=$(du -h "${BACKUP_DIR}/${FILENAME}" | cut -f1)
echo "Backup complete: ${BACKUP_DIR}/${FILENAME} (${SIZE})"

# Clean old backups
DELETED=$(find "$BACKUP_DIR" -name "orenoiomni_*.sql.gz" -mtime +"$KEEP_DAYS" -print -delete | wc -l)
if [ "$DELETED" -gt 0 ]; then
    echo "Cleaned up ${DELETED} backup(s) older than ${KEEP_DAYS} days."
fi
