# کارما (KARMA)

سامانه فارسی مدیریت پروژه، میزکار و همکاری تیمی بر پایه Django + PostgreSQL + Bootstrap RTL.

نسخه فعلی: **KARMA 1.5.0** — موتور پیشرفت واقعی، ثبت ساعات کاری، تایمر و گزارش ماهانه شمسی.

## امکانات موجود

- چند میزکار برای هر کاربر
- مالک و مدیر میزکار
- افزودن همکار فقط با نام و شماره موبایل
- اتصال خودکار همکار دعوت‌شده به حساب کاربری پس از ثبت‌نام با همان شماره
- جداسازی عضویت میزکار از دسترسی پروژه
- تعیین پروژه‌های مجاز هنگام افزودن همکار
- صفحه مدیریت دسترسی اعضا برای هر پروژه
- فهرست پروژه‌های هر میزکار
- اولویت پروژه: فوری، خیلی بالا، بالا، عادی، پایین
- فیلتر و مرتب‌سازی پروژه‌ها بر اساس اولویت، پیشرفت، موعد و آخرین تغییر
- پروژه، وضعیت، مدیر، تاریخ شروع/پایان و درصد پیشرفت
- فهرست وظایف، وظیفه، مسئول، اولویت، وضعیت و چک‌لیست
- بورد Kanban با Drag & Drop وضعیت وظایف
- Timeline / مسیر فعالیت و پیشرفت پروژه
- دو چت گروهی پیش‌فرض برای هر پروژه: «پیگیری» و «مستندات»
- چت خصوصی Project-Scoped بین اعضای همان پروژه
- مرکز یکپارچه همه گفتگوهای فردی و گروهی
- ارسال متن و چند فایل در هر پیام
- نمایش مستقیم عکس، ویدئو و صوت در چت
- ارسال PDF و فایل‌های عمومی
- ضبط مستقیم پیام صوتی با MediaRecorder مرورگر
- ثبت خودکار فایل‌های «چت مستندات» در مرکز مستندات پروژه
- مستندات متنی، تصویر، ویدئو، صوت و فایل
- نامه اداری داخلی، وارده و صادره با شماره خودکار
- یادداشت شخصی و چک‌لیست یادداشت
- اعلان درون‌برنامه‌ای با Deep Link
- اعلان پیام‌های گروهی و خصوصی
- داشبورد شخصی و نمودار وضعیت پروژه‌ها
- جستجوی سراسری در پروژه، وظیفه، سند و نامه
- رابط فارسی RTL با Bootstrap، Font Awesome و Vazirmatn
- طراحی Responsive برای دسکتاپ و موبایل
- پنل Django Admin
- Migrationهای اولیه آماده
- PostgreSQL به‌عنوان دیتابیس پیش‌فرض
- ثبت دستی ساعت کاری با تقویم شمسی و ساعت شروع/پایان
- تایمر شروع/اتمام روی پروژه و وظیفه
- گزارش ساعات کاری شخصی، پروژه‌ای، میزکار و ماه شمسی
- امکان حذف گزارش ساعت توسط کاربر و مدیریت توسط مدیر پروژه/میز
- بازگشایی کار تکمیل‌شده و برداشتن تیک توسط کارفرما یا مسئول پروژه

## معماری دسترسی

```text
User
  ↓
WorkspaceMember
  ↓
ProjectMember
```

عضو بودن در میزکار به معنی مشاهده همه پروژه‌های آن میز نیست. مالک/مدیر میزکار برای هر فرد پروژه‌های مجاز را مشخص می‌کند.

## ساختار هر پروژه

```text
Project
├── Overview / Dashboard
├── Task Lists
├── Tasks
├── Checklists
├── Kanban Board
├── Members & Access
├── Follow-up Chat     (پیش‌فرض)
├── Documents Chat     (پیش‌فرض)
├── Private Project Chats
├── Document Center
├── Letters
└── Activity Timeline
```

## نصب آسان روی Ubuntu / Debian

پس از Extract فایل ZIP:

```bash
chmod +x install.sh
./install.sh
```

اسکریپت نصب در صورت دسترسی به `apt` موارد زیر را انجام می‌دهد:

1. نصب Python/venv و PostgreSQL
2. ایجاد Role و Database اختصاصی `karma`
3. ایجاد `.venv`
4. نصب پکیج‌های Python
5. ساخت فایل `.env`
6. اجرای migrationها
7. `collectstatic`
8. ساخت داده و کاربر نمایشی

سپس:

```bash
./run.sh
```

و سایت از آدرس زیر در دسترس است:

```text
http://SERVER-IP:8000/
```

### حساب نمایشی

```text
شماره/نام کاربری: 09170000000
رمز: 123456
```

برای غیرفعال‌کردن Seed دمو:

```bash
KARMA_SEED_DEMO=0 ./install.sh
```

## تنظیم PostgreSQL سفارشی هنگام نصب

```bash
KARMA_DB_NAME=karma \
KARMA_DB_USER=karma \
KARMA_DB_PASSWORD='StrongPassword' \
./install.sh
```

## نصب دستی

PostgreSQL باید در دسترس باشد. سپس:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# مقادیر دیتابیس و SECRET_KEY را ویرایش کنید
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py seed_demo   # اختیاری
python manage.py runserver 0.0.0.0:8000
```

## اجرای Production

`run-production.sh` برای اجرای Gunicorn قرار داده شده است:

```bash
./run-production.sh
```

برای Production واقعی باید `DEBUG=0`، دامنه در `ALLOWED_HOSTS` و `CSRF_TRUSTED_ORIGINS` تنظیم شود و Nginx/HTTPS برای Static/Media جلوی Gunicorn قرار گیرد.

## متغیرهای مهم `.env`

```text
SECRET_KEY
DEBUG
ALLOWED_HOSTS
CSRF_TRUSTED_ORIGINS
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_HOST
POSTGRES_PORT
KARMA_MAX_UPLOAD_MB
```

## توسعه محلی بدون PostgreSQL

فقط برای تست محلی می‌توان در `.env` نوشت:

```text
DB_ENGINE=sqlite
```

اما نصب استاندارد و معماری اصلی کارما بر PostgreSQL تنظیم شده است.

## ساختار سورس

```text
accounts/        حساب کاربری و پروفایل
workspaces/      میزکار، همکار و عضویت
projects/        پروژه، دسترسی، وظیفه، فهرست، چک‌لیست، بورد، Timeline
communication/   چت، Voice، مستندات، نامه، یادداشت، اعلان
dashboard/       داشبورد، نمودار و جستجو
config/          تنظیمات Django/PostgreSQL
static/          CSS و JavaScript
templates/       رابط Bootstrap RTL
```

## نکات توسعه بعدی

ساختار پروژه به‌صورت Modular Monolith نگه داشته شده تا در مراحل بعد بتوان قابلیت‌هایی مانند WebSocket realtime، Redis/Celery، Object Storage، نسخه‌بندی اسناد، گانت، تقویم شمسی پیشرفته، گردش مکاتبات، Approval Workflow و گزارش‌های مدیریتی پیشرفته را بدون بازطراحی کل هسته اضافه کرد.

## KARMA 1.4.0 — موتور پیشرفت واقعی

در نسخه 1.4.0 پیشرفت پروژه دیگر صرفاً بر اساس تعداد وظایف Done نیست. هر وظیفه‌ای که چک‌لیست داشته باشد از نسبت تیک‌های همان چک‌لیست درصد می‌گیرد و وظیفه‌ای که با دکمه «تکمیل شد» یا ستون Done کانبان تکمیل شود ۱۰۰٪ محاسبه می‌شود. پیشرفت پروژه میانگین این درصدهای واقعی است.

برای ارتقای نصب Production موجود، فایل ZIP را در `/root/karma/` قرار دهید، Extract کنید و `sudo ./upgrade-production.sh` را اجرا کنید. PostgreSQL قبل از Migration به‌صورت خودکار Backup می‌شود.
