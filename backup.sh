#!/usr/bin/env bash
set -euo pipefail

PROJECT="${COMPOSE_PROJECT:-barq-assessment}"
CONTAINER="${POSTGRES_CONTAINER:-postgres}"
DB_USER="${POSTGRES_USER:-barq_app}"
DB_NAME="${POSTGRES_DB:-barq_tasks}"
BACKUP_DIR="${BACKUP_DIR:-backups}"

mkdir -p "$BACKUP_DIR"

if [[ ! -f .env ]]; then
  echo "FAIL: .env not found" >&2
  exit 1
fi

set -a
source ./.env
set +a

: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is not set}"

if ! docker inspect "$CONTAINER" >/dev/null 2>&1; then
  echo "FAIL: PostgreSQL container '$CONTAINER' does not exist" >&2
  exit 1
fi

STATUS="$(docker inspect "$CONTAINER" --format '{{.State.Status}}')"

if [[ "$STATUS" != "running" ]]; then
  echo "FAIL: PostgreSQL container is not running" >&2
  exit 1
fi

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql"

echo "Creating PostgreSQL backup..."
echo "database=$DB_NAME"
echo "container=$CONTAINER"
echo "output=$BACKUP_FILE"

docker exec \
  -e PGPASSWORD="$POSTGRES_PASSWORD" \
  "$CONTAINER" \
  pg_dump \
    --username="$DB_USER" \
    --dbname="$DB_NAME" \
    --no-owner \
    --no-privileges \
    --format=plain \
  > "$BACKUP_FILE"

if [[ ! -s "$BACKUP_FILE" ]]; then
  echo "FAIL: backup file is empty" >&2
  rm -f "$BACKUP_FILE"
  exit 1
fi

echo "PASS: PostgreSQL backup created"
echo "file=$BACKUP_FILE"
echo "size=$(du -h "$BACKUP_FILE" | cut -f1)"
