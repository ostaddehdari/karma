#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "این اسکریپت را با sudo اجرا کنید: sudo ./upgrade-production.sh"
  exit 1
fi

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="/var/www/karma/current"
BACKUP_DIR="/var/backups/karma"
STAMP="$(date +%Y%m%d-%H%M%S)"

log(){ printf '\n\033[1;36m[KARMA 1.5 UPGRADE]\033[0m %s\n' "$*"; }
fail(){ printf '\n\033[1;31m[خطا]\033[0m %s\n' "$*" >&2; exit 1; }

[[ -d "$APP_DIR" ]] || fail "نصب موجود کارما در $APP_DIR پیدا نشد."
[[ -x "$APP_DIR/.venv/bin/python" ]] || fail "Virtualenv کارما پیدا نشد."
[[ -f "$APP_DIR/.env" ]] || fail ".env نصب موجود پیدا نشد."
mkdir -p "$BACKUP_DIR"

log "۱/۹ — بکاپ کد فعلی..."
tar --exclude='.venv' --exclude='media' --exclude='staticfiles' -czf "$BACKUP_DIR/karma-code-before-1.5.0-$STAMP.tar.gz" -C "$APP_DIR" .

read_env(){
  local key="$1" default="$2" value
  value="$(grep -E "^${key}=" "$APP_DIR/.env" | tail -n1 | cut -d= -f2- || true)"
  value="${value%\"}"; value="${value#\"}"; value="${value%\'}"; value="${value#\'}"
  printf '%s' "${value:-$default}"
}
DB_NAME="$(read_env POSTGRES_DB karma)"
DB_USER="$(read_env POSTGRES_USER karma)"
DB_PASS="$(read_env POSTGRES_PASSWORD karma_change_me)"
DB_HOST="$(read_env POSTGRES_HOST 127.0.0.1)"
DB_PORT="$(read_env POSTGRES_PORT 5432)"

log "۲/۹ — بکاپ کامل PostgreSQL قبل از Migration..."
DB_BACKUP="$BACKUP_DIR/karma-db-before-1.5.0-$STAMP.dump"
command -v pg_dump >/dev/null 2>&1 || fail "pg_dump نصب نیست؛ برای امنیت داده‌ها ارتقا متوقف شد."
PGPASSWORD="$DB_PASS" pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -Fc "$DB_NAME" > "$DB_BACKUP"
echo "DB backup: $DB_BACKUP"

log "۳/۹ — انتقال کد جدید با حفظ دیتابیس، .env، media، staticfiles و virtualenv..."
rsync -a --delete \
  --exclude='.env' --exclude='.venv/' --exclude='media/' --exclude='staticfiles/' --exclude='db.sqlite3' \
  "$SRC_DIR/" "$APP_DIR/"

log "۴/۹ — وابستگی‌های Python..."
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

cd "$APP_DIR"
log "۵/۹ — بررسی Django..."
"$APP_DIR/.venv/bin/python" manage.py check

log "۶/۹ — Migration امن دیتابیس (ایجاد جدول ساعات کاری)..."
"$APP_DIR/.venv/bin/python" manage.py migrate --noinput

log "۷/۹ — جمع‌آوری Static شامل Date Picker شمسی..."
"$APP_DIR/.venv/bin/python" manage.py collectstatic --noinput

log "۸/۹ — Permission امن..."
chown -R root:www-data "$APP_DIR"
find "$APP_DIR" -type d -not -path "$APP_DIR/media*" -exec chmod 750 {} +
find "$APP_DIR" -type f -not -path "$APP_DIR/media*" -exec chmod 640 {} +
find "$APP_DIR/.venv/bin" -maxdepth 1 -type f -exec chmod 755 {} +
mkdir -p "$APP_DIR/media"
chown -R www-data:www-data "$APP_DIR/media"
chmod -R u+rwX,g+rwX "$APP_DIR/media"

log "۹/۹ — Restart فقط سرویس KARMA..."
systemctl daemon-reload
systemctl restart karma
sleep 2
systemctl --no-pager --full status karma | sed -n '1,24p'
test -S /run/karma/karma.sock && echo "OK: /run/karma/karma.sock" || fail "Socket کارما ساخته نشد."

cat <<MSG

============================================================
KARMA 1.5.0 با موفقیت ارتقا یافت.

قابلیت‌های جدید:
- ثبت ساعت دستی با تقویم شمسی و ساعت شروع/پایان
- تایمر شروع/اتمام پروژه و وظیفه
- حذف گزارش ساعت
- گزارش شخصی، پروژه‌ای، میزکار و ماه شمسی
- نمودار ساعات روزانه ماه
- بازگشایی کار/چک‌لیست توسط کارفرما و مسئول پروژه

PostgreSQL قبلی و همه داده‌های موجود حفظ شدند.
Backup دیتابیس:
  $DB_BACKUP

Nginx نیاز به تغییر ندارد.
تست:
  curl -k -I https://5.61.27.185/karma/
============================================================
MSG
