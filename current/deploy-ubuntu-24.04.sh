#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "این اسکریپت را با sudo اجرا کنید: sudo ./deploy-ubuntu-24.04.sh"
  exit 1
fi

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="/var/www/karma"
APP_DIR="$APP_ROOT/current"
DB_NAME="${KARMA_DB_NAME:-karma}"
DB_USER="${KARMA_DB_USER:-karma}"
DB_PASS="${KARMA_DB_PASSWORD:-$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(28))
PY
)}"
SECRET="${KARMA_SECRET_KEY:-$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(60))
PY
)}"

log(){ printf '\n\033[1;35m[KARMA DEPLOY]\033[0m %s\n' "$*"; }

log "نصب پیش‌نیازهای لازم بدون دست‌زدن به سایت‌های دیگر..."
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip postgresql postgresql-contrib libpq-dev build-essential rsync
systemctl enable --now postgresql

log "ایجاد/به‌روزرسانی PostgreSQL..."
runuser -u postgres -- psql -v ON_ERROR_STOP=1 --set=dbuser="$DB_USER" --set=dbpass="$DB_PASS" --set=dbname="$DB_NAME" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'dbuser', :'dbpass')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = :'dbuser')\gexec
SELECT format('ALTER ROLE %I WITH LOGIN PASSWORD %L', :'dbuser', :'dbpass')\gexec
SELECT format('CREATE DATABASE %I OWNER %I', :'dbname', :'dbuser')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = :'dbname')\gexec
SQL

log "کپی برنامه در $APP_DIR ..."
mkdir -p "$APP_DIR"
rsync -a --delete \
  --exclude '.venv' --exclude '.env' --exclude 'media/' --exclude 'staticfiles/' \
  "$SRC_DIR/" "$APP_DIR/"
mkdir -p "$APP_DIR/media" "$APP_DIR/staticfiles"

log "ساخت محیط مجازی و نصب Python dependencies..."
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip wheel
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

log "نوشتن تنظیمات Production برای https://5.61.27.185/karma/ ..."
cat > "$APP_DIR/.env" <<ENV
SECRET_KEY=$SECRET
DEBUG=0
ALLOWED_HOSTS=5.61.27.185,127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=https://5.61.27.185
APP_PREFIX=/karma
TIME_ZONE=Asia/Tehran
DB_ENGINE=postgresql
POSTGRES_DB=$DB_NAME
POSTGRES_USER=$DB_USER
POSTGRES_PASSWORD=$DB_PASS
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
DB_CONN_MAX_AGE=60
KARMA_MAX_UPLOAD_MB=200
ENV
chown root:www-data "$APP_DIR/.env"
chmod 640 "$APP_DIR/.env"

log "Migration و static files..."
cd "$APP_DIR"
"$APP_DIR/.venv/bin/python" manage.py migrate --noinput
"$APP_DIR/.venv/bin/python" manage.py collectstatic --noinput
"$APP_DIR/.venv/bin/python" manage.py check --deploy

if [[ "${KARMA_SEED_DEMO:-0}" == "1" ]]; then
  log "ساخت داده نمایشی به درخواست شما..."
  "$APP_DIR/.venv/bin/python" manage.py seed_demo
fi

log "تنظیم مالکیت فایل‌ها..."
chown -R root:www-data "$APP_ROOT"
find "$APP_ROOT" -type d -exec chmod 750 {} +
find "$APP_ROOT" -type f -exec chmod 640 {} +
find "$APP_DIR/.venv/bin" -maxdepth 1 -type f -exec chmod 755 {} +
chmod 750 "$APP_DIR/scripts/backup.sh" "$APP_DIR/scripts/restore.sh"
chown -R www-data:www-data "$APP_DIR/media"
chmod -R u+rwX,g+rwX "$APP_DIR/media"
install -d -o www-data -g www-data -m 750 /var/backups/karma

log "نصب سرویس systemd..."
cp "$APP_DIR/karma.service" /etc/systemd/system/karma.service
systemctl daemon-reload
systemctl enable --now karma.service
sleep 2
systemctl --no-pager --full status karma.service || true

log "فعال‌سازی بکاپ روزانه..."
install -m 644 "$APP_DIR/scripts/karma-backup.service" /etc/systemd/system/karma-backup.service
install -m 644 "$APP_DIR/scripts/karma-backup.timer" /etc/systemd/system/karma-backup.timer
systemctl daemon-reload
systemctl enable --now karma-backup.timer

log "نصب snippet امن Nginx (بدون تغییر خودکار سایت‌های موجود)..."
install -m 644 "$APP_DIR/nginx-karma-location.conf" /etc/nginx/snippets/karma-location.conf

cat <<'MSG'

============================================================
بخش Django/Gunicorn/PostgreSQL کارما نصب شد.

برای اتصال به Nginx فعلی فقط باید خط زیر را داخل همان server { ... }
که HTTPS آدرس 5.61.27.185 را پاسخ می‌دهد اضافه کنید:

    include /etc/nginx/snippets/karma-location.conf;

سپس:
    sudo nginx -t
    sudo systemctl reload nginx

برای اینکه من فایل دقیق Nginx را بدون ریسک ۵ سایت دیگر مشخص کنم، خروجی این دستور را بفرستید:
    sudo nginx -T 2>&1 | sed -n '1,260p'

پس از reload آدرس برنامه:
    https://5.61.27.185/karma/

وضعیت برنامه:
    sudo systemctl status karma
لاگ زنده:
    sudo journalctl -u karma -f
============================================================
MSG
