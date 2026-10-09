#!/usr/bin/env bash
set -Eeuo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"
[[ -d .venv ]] || { echo "ابتدا ./install.sh را اجرا کنید."; exit 1; }
source .venv/bin/activate
exec gunicorn config.wsgi:application --bind "${KARMA_BIND:-0.0.0.0:8000}" --workers "${KARMA_WORKERS:-3}" --timeout 120
