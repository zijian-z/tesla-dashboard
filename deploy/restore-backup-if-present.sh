#!/bin/sh
set -eu

: "${POSTGRES_USER:=teslamate}"
: "${POSTGRES_DB:=teslamate}"

BACKUP_SOURCE_DIR="${BACKUP_SOURCE_DIR:-/backup-source}"

if [ ! -d "$BACKUP_SOURCE_DIR" ]; then
  echo "No backup source directory found at $BACKUP_SOURCE_DIR; skipping restore."
  exit 0
fi

backup_file=""

for pattern in \
  teslamate.bck \
  teslamate.sql \
  teslamate.dump \
  teslamate.backup \
  teslamate.sql.gz \
  teslamate.bck.gz \
  teslamate.dump.gz \
  teslamate.backup.gz \
  "*.bck" \
  "*.sql" \
  "*.dump" \
  "*.backup" \
  "*.sql.gz" \
  "*.bck.gz" \
  "*.dump.gz" \
  "*.backup.gz"
do
  for candidate in "$BACKUP_SOURCE_DIR"/$pattern; do
    if [ -f "$candidate" ]; then
      backup_file="$candidate"
      break 2
    fi
  done
done

if [ -z "$backup_file" ]; then
  echo "No TeslaMate database backup found in $BACKUP_SOURCE_DIR; starting with an empty database."
  exit 0
fi

echo "Restoring TeslaMate database backup: $backup_file"

prepare_database_for_restore() {
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
DROP SCHEMA IF EXISTS public CASCADE;
DROP SCHEMA IF EXISTS private CASCADE;
CREATE SCHEMA public;
CREATE EXTENSION IF NOT EXISTS cube WITH SCHEMA public;
CREATE EXTENSION IF NOT EXISTS earthdistance WITH SCHEMA public;
SQL
}

restore_dump_or_sql() {
  candidate="$1"

  if pg_restore --list "$candidate" >/dev/null 2>&1; then
    pg_restore --verbose --no-owner --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" "$candidate"
  else
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" < "$candidate"
  fi
}

clear_restored_teslamate_tokens() {
  echo "Clearing restored TeslaMate API tokens so this instance can be authorized fresh."

  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
DO $$
DECLARE
  token_table record;
  cleared_count integer := 0;
BEGIN
  FOR token_table IN
    SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE table_name = 'tokens'
      AND table_schema IN ('private', 'public')
      AND table_type = 'BASE TABLE'
  LOOP
    EXECUTE format(
      'TRUNCATE TABLE %I.%I RESTART IDENTITY CASCADE',
      token_table.table_schema,
      token_table.table_name
    );
    cleared_count := cleared_count + 1;
    RAISE NOTICE 'Cleared restored TeslaMate tokens from %.%', token_table.table_schema, token_table.table_name;
  END LOOP;

  IF cleared_count = 0 THEN
    RAISE NOTICE 'No TeslaMate tokens table found to clear.';
  END IF;
END
$$;
SQL
}

prepare_database_for_restore

case "$backup_file" in
  *.sql|*.bck)
    restore_dump_or_sql "$backup_file"
    ;;
  *.sql.gz|*.bck.gz)
    tmp_file="/tmp/teslamate-restore"
    gzip -dc "$backup_file" > "$tmp_file"
    restore_dump_or_sql "$tmp_file"
    rm -f "$tmp_file"
    ;;
  *.dump|*.backup)
    restore_dump_or_sql "$backup_file"
    ;;
  *.dump.gz|*.backup.gz)
    tmp_file="/tmp/teslamate-restore.dump"
    gzip -dc "$backup_file" > "$tmp_file"
    restore_dump_or_sql "$tmp_file"
    rm -f "$tmp_file"
    ;;
  *)
    echo "Unsupported backup format: $backup_file" >&2
    exit 1
    ;;
esac

clear_restored_teslamate_tokens

echo "TeslaMate database backup restore completed."
