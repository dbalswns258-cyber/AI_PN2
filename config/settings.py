import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PRODUCTION = os.environ.get('AI_PN2_ENV', 'development') == 'production'
DATA_DIR = Path(os.environ.get('AI_PN2_DATA_DIR', BASE_DIR.parent / 'ai-pn2-data')).resolve()
if DATA_DIR == BASE_DIR or BASE_DIR in DATA_DIR.parents:
    raise RuntimeError('AI_PN2_DATA_DIR must be outside the Git checkout.')
SECRET_KEY = os.environ.get('AI_PN2_SECRET_KEY', '')
if not SECRET_KEY:
    secret_file = DATA_DIR / 'django-secret-key'
    if secret_file.exists():
        SECRET_KEY = secret_file.read_text().strip()
    else:
        raise RuntimeError('Run python scripts/prepare_data.py before manage.py.')
DEBUG = not PRODUCTION and os.environ.get('AI_PN2_DEBUG', '0') == '1'
external_hostname = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '').strip()
default_hosts = '127.0.0.1,localhost' + (',' + external_hostname if external_hostname else '')
ALLOWED_HOSTS = [host.strip() for host in os.environ.get('AI_PN2_ALLOWED_HOSTS', default_hosts).split(',') if host.strip()]
if not PRODUCTION:
    ALLOWED_HOSTS.append('testserver')
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.environ.get('AI_PN2_CSRF_TRUSTED_ORIGINS',
    'https://' + external_hostname if external_hostname else '').split(',') if origin.strip()]
INSTALLED_APPS = ['django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions',
                  'django.contrib.messages', 'django.contrib.staticfiles', 'projects']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware',
              'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware',
              'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware',
              'django.middleware.clickjacking.XFrameOptionsMiddleware']
if PRODUCTION:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [BASE_DIR / 'templates'],
              'APP_DIRS': True, 'OPTIONS': {'context_processors': [
                  'django.template.context_processors.request', 'django.contrib.auth.context_processors.auth',
                  'django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'config.wsgi.application'
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': DATA_DIR / 'db.sqlite3',
                         'OPTIONS': {'timeout': 20}}}
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = DATA_DIR / 'staticfiles'
STORAGES = {'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
            'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage' if PRODUCTION
                            else 'django.contrib.staticfiles.storage.StaticFilesStorage'}}
MEDIA_ROOT = DATA_DIR / 'files'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'login'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 8 * 60 * 60
SESSION_COOKIE_SECURE = os.environ.get('AI_PN2_HTTPS', '1' if PRODUCTION else '0') == '1'
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
SECURE_SSL_REDIRECT = SESSION_COOKIE_SECURE
SECURE_REDIRECT_EXEMPT = [r'^healthz/$']
SECURE_HSTS_SECONDS = 3600 if SESSION_COOKIE_SECURE else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
if os.environ.get('AI_PN2_TRUST_PROXY', '0') == '1':
    # Enable only behind a hosting proxy that overwrites this header.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000
FILE_UPLOAD_PERMISSIONS = 0o600
