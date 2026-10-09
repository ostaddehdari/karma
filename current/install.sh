#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

log(){ printf '\n\033[1;35m[KARMA]\033[0m %s\n' "$*"; }
fail(){ printf '\n\033[1;31m[ERROR]\033[0m %s\n' "$*" >&2; exit 1; }

command -v python3 >/dev/null 2>&1 || fail "python3 پیدا نشد."

if [[ "${KARMA_SKIP_SYSTEM_PACKAGES:-0}" != "1" ]] && command -v apt-get >/dev/null 2>&1; then
  log "نصب پیش‌نیازهای سیستم و PostgreSQL..."
  SUDO=""
  [[ "$(id -u)" -ne 0 ]] && SUDO="sudo"
  $SUDO apt-get update
  $SUDO apt-get install -y python3 python3-venv python3-pip postgresql postgresql-contrib libpq-dev build-essential
  $SUDO systemctl enable --now postgresql >/dev/null 2>&1 || true
fi

DB_NAME="${KARMA_DB_NAME:-karma}"
DB_USER="${KARMA_DB_USER:-karma}"
DB_PASS="${KARMA_DB_PASSWORD:-$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(24))
PY
)}"
SECRET="${KARMA_SECRET_KEY:-$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(50))
PY
)}"

if command -v psql >/dev/null 2>&1; then
  log "آماده‌سازی دیتابیس PostgreSQL..."
  if [[ "$(id -u)" -eq 0 ]]; then
    PSQL=(runuser -u postgres -- psql)
  else
    PSQL=(sudo -u postgres psql)
  fi
  "${PSQL[@]}" -v ON_ERROR_STOP=1 --set=dbuser="$DB_USER" --set=dbpass="$DB_PASS" --set=dbname="$DB_NAME" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'dbuser', :'dbpass')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = :'dbuser')\gexec
SELECT format('ALTER ROLE %I WITH LOGIN PASSWORD %L', :'dbuser', :'dbpass')\gexec
SELECT format('CREATE DATABASE %I OWNER %I', :'dbname', :'dbuser')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = :'dbname')\gexec
SQL
else
  fail "PostgreSQL/psql نصب نیست. روی Ubuntu/Debian اسکریپت را بدون KARMA_SKIP_SYSTEM_PACKAGES اجرا کنید."
fi

log "ساخت محیط مجازی Python..."
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip wheel
python -m pip install -r requirements.txt

cat > .env <<ENV
SECRET_KEY=$SECRET
DEBUG=${KARMA_DEBUG:-0}
ALLOWED_HOSTS=${KARMA_ALLOWED_HOSTS:-127.0.0.1,localhost}
CSRF_TRUSTED_ORIGINS=${KARMA_CSRF_TRUSTED_ORIGINS:-}
TIME_ZONE=${KARMA_TIME_ZONE:-Asia/Tehran}
DB_ENGINE=postgresql
POSTGRES_DB=$DB_NAME
POSTGRES_USER=$DB_USER
POSTGRES_PASSWORD=$DB_PASS
POSTGRES_HOST=${KARMA_DB_HOST:-127.0.0.1}
POSTGRES_PORT=${KARMA_DB_PORT:-5432}
DB_CONN_MAX_AGE=60
KARMA_MAX_UPLOAD_MB=${KARMA_MAX_UPLOAD_MB:-100}
KARMA_MAX_FILES_PER_UPLOAD=${KARMA_MAX_FILES_PER_UPLOAD:-10}
KARMA_MAX_TOTAL_UPLOAD_MB=${KARMA_MAX_TOTAL_UPLOAD_MB:-150}
ENV
chmod 600 .env

log "اجرای migrationها..."
python manage.py migrate
python manage.py collectstatic --noinput >/dev/null
mkdir -p media

if [[ "${KARMA_SEED_DEMO:-0}" == "1" ]]; then
  log "ساخت داده و کاربر نمایشی..."
  python manage.py seed_demo
fi

log "نصب انجام شد."
printf '\nاجرای سایت:\n  cd %q\n  ./run.sh\n\n' "$APP_DIR"
printf 'آدرس پیش‌فرض: http://127.0.0.1:8000/\n'
if [[ "${KARMA_SEED_DEMO:-0}" == "1" ]]; then
  printf 'کاربر نمونه: 09170000000\nرمز نمونه: 123456\n'
fi
printf '\nرمز دیتابیس در فایل .env ذخیره شده است.\n'
