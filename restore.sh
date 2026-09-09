#!/usr/bin/env bash
set -euo pipefail

CONTAINER="${POSTGRES_CONTAINER:-postgres}"
DB_USER="${POSTGRES_USER:-barq_app}"
DB_NAME="${POSTGRES_DB:-barq_tasks}"

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <backup.sql>" >&2
  exit 1
fi

BACKUP_FILE="$1"

if [[ ! -f "$BACKUP_FILE" ]]; then
  echo "FAIL: backup file not found: $BACKUP_FILE" >&2
  exit 1
fi

if [[ ! -s "$BACKUP_FILE" ]]; then
  echo "FAIL: backup file is empty: $BACKUP_FILE" >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "FAIL: .env not found" >&2
  exit 1
fi

set -a
source ./.env
set +a

: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is not set}"

STATUS="$(docker inspect "$CONTAINER" --format '{{.State.Status}}' 2>/dev/null || true)"

if [[ "$STATUS" != "running" ]]; then
  echo "FAIL: PostgreSQL container '$CONTAINER' is not running" >&2
  exit 1
fi

echo "Restoring PostgreSQL backup..."
echo "database=$DB_NAME"
echo "container=$CONTAINER"
echo "source=$BACKUP_FILE"

echo "Resetting public schema..."

docker exec \
  -e PGPASSWORD="$POSTGRES_PASSWORD" \
  "$CONTAINER" \
  psql \
    --username="$DB_USER" \
    --dbname="$DB_NAME" \
    --set=ON_ERROR_STOP=1 \
    --command="DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

echo "Loading backup..."

docker exec -i \
  -e PGPASSWORD="$POSTGRES_PASSWORD" \
  "$CONTAINER" \
  psql \
    --username="$DB_USER" \
    --dbname="$DB_NAME" \
    --set=ON_ERROR_STOP=1 \
    --quiet \
  < "$BACKUP_FILE"

echo "Verifying restored database..."

TABLE_EXISTS="$(
  docker exec \
    -e PGPASSWORD="$POSTGRES_PASSWORD" \
    "$CONTAINER" \
    psql \
      --username="$DB_USER" \
      --dbname="$DB_NAME" \
      --tuples-only \
      --no-align \
      --command="SELECT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema='public'
        AND table_name='records'
      );"
)"

if [[ "$TABLE_EXISTS" != "t" ]]; then
  echo "FAIL: records table was not restored" >&2
  exit 1
fi

echo "PASS: PostgreSQL backup restored successfully"
