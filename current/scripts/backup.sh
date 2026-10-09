#!/usr/bin/env bash
set -Eeuo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${KARMA_BACKUP_DIR:-$APP_DIR/backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
KEEP_DAYS="${KARMA_BACKUP_KEEP_DAYS:-14}"
mkdir -p "$BACKUP_DIR/$STAMP"
set -a; source "$APP_DIR/.env"; set +a
pg_dump --format=custom --no-owner --no-acl \
  --host="$POSTGRES_HOST" --port="$POSTGRES_PORT" --username="$POSTGRES_USER" \
  --file="$BACKUP_DIR/$STAMP/database.dump" "$POSTGRES_DB"
tar -C "$APP_DIR" -czf "$BACKUP_DIR/$STAMP/media.tar.gz" media
sha256sum "$BACKUP_DIR/$STAMP/database.dump" "$BACKUP_DIR/$STAMP/media.tar.gz" > "$BACKUP_DIR/$STAMP/SHA256SUMS"
find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -mtime "+$KEEP_DAYS" -print -exec rm -rf -- {} +
printf 'Backup created: %s\n' "$BACKUP_DIR/$STAMP"
