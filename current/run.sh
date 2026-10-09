#!/usr/bin/env bash
set -Eeuo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"
[[ -d .venv ]] || { echo "ابتدا ./install.sh را اجرا کنید."; exit 1; }
source .venv/bin/activate
exec python manage.py runserver "${KARMA_BIND:-0.0.0.0:8000}"
