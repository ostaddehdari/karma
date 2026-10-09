#!/usr/bin/env bash
set -Eeuo pipefail
[[ $# -eq 1 ]] || { echo "Usage: $0 /absolute/path/to/backup" >&2; exit 2; }
SOURCE="$(realpath "$1")"
[[ -f "$SOURCE/database.dump" && -f "$SOURCE/media.tar.gz" && -f "$SOURCE/SHA256SUMS" ]] || { echo "Invalid backup" >&2; exit 2; }
(cd "$SOURCE" && sha256sum -c SHA256SUMS)
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a; source "$APP_DIR/.env"; set +a
pg_restore --clean --if-exists --no-owner --no-acl \
  --host="$POSTGRES_HOST" --port="$POSTGRES_PORT" --username="$POSTGRES_USER" \
  --dbname="$POSTGRES_DB" "$SOURCE/database.dump"
mkdir -p "$APP_DIR/media"
tar -C "$APP_DIR" -xzf "$SOURCE/media.tar.gz"
"$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" migrate --noinput
printf 'Restore completed from: %s\n' "$SOURCE"
