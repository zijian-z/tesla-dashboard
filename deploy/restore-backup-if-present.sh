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

restore_dump_or_sql() {
  candidate="$1"

  if pg_restore --list "$candidate" >/dev/null 2>&1; then
    pg_restore --verbose --no-owner --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" "$candidate"
  else
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" < "$candidate"
  fi
}

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

echo "TeslaMate database backup restore completed."
