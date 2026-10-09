from pathlib import Path
import os
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path):
    """Tiny .env loader to keep deployment dependencies minimal."""
    if not path.exists():
        return
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_dotenv(BASE_DIR / '.env')

DEBUG = os.environ.get('DEBUG', '0').lower() in {'1', 'true', 'yes', 'on'}
SECRET_KEY = os.environ.get('SECRET_KEY', '')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'development-only-change-me'
    else:
        raise ImproperConfigured('SECRET_KEY must be set in production.')
ALLOWED_HOSTS = [x.strip() for x in os.environ.get('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',') if x.strip()]
CSRF_TRUSTED_ORIGINS = [x.strip() for x in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if x.strip()]

# Supports production deployment below a URL prefix such as /karma.
APP_PREFIX = os.environ.get('APP_PREFIX', '').strip()
if APP_PREFIX:
    if not APP_PREFIX.startswith('/'):
        APP_PREFIX = '/' + APP_PREFIX
    APP_PREFIX = APP_PREFIX.rstrip('/')
FORCE_SCRIPT_NAME = APP_PREFIX or None
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'workspaces',
    'projects',
    'communication',
    'timetracking',
    'dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
            'dashboard.context_processors.shell_context',
        ]
    },
}]
WSGI_APPLICATION = 'config.wsgi.application'

# PostgreSQL is the default database for KARMA.
# SQLite is available only as an explicit local/test fallback (DB_ENGINE=sqlite).
if os.environ.get('DB_ENGINE', 'postgresql').lower() == 'sqlite':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('POSTGRES_DB', 'karma'),
            'USER': os.environ.get('POSTGRES_USER', 'karma'),
            'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
            'HOST': os.environ.get('POSTGRES_HOST', '127.0.0.1'),
            'PORT': os.environ.get('POSTGRES_PORT', '5432'),
            'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', '60')),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fa-ir'
TIME_ZONE = os.environ.get('TIME_ZONE', 'Asia/Tehran')
USE_I18N = True
USE_TZ = True

STATIC_URL = f'{APP_PREFIX}/static/' if APP_PREFIX else '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = f'{APP_PREFIX}/media/' if APP_PREFIX else '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.environ.get('FILE_UPLOAD_MAX_MEMORY_SIZE', 25 * 1024 * 1024))
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.environ.get('DATA_UPLOAD_MAX_MEMORY_SIZE', 120 * 1024 * 1024))
KARMA_MAX_UPLOAD_MB = int(os.environ.get('KARMA_MAX_UPLOAD_MB', '100'))
KARMA_MAX_FILES_PER_UPLOAD = int(os.environ.get('KARMA_MAX_FILES_PER_UPLOAD', '10'))
KARMA_MAX_TOTAL_UPLOAD_MB = int(os.environ.get('KARMA_MAX_TOTAL_UPLOAD_MB', '150'))

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_PATH = f'{APP_PREFIX}/' if APP_PREFIX else '/'
CSRF_COOKIE_PATH = f'{APP_PREFIX}/' if APP_PREFIX else '/'
CSRF_COOKIE_HTTPONLY = False  # needed by the voice AJAX uploader
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'same-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', '1').lower() in {'1', 'true', 'yes', 'on'}
    SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
