# settings.py
import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-your-secret-key-here')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'drf_yasg',
    'corsheaders',
    'django_filters',
    
    # Local apps
    'flashcroquis',  # Notre application principale
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ApiFlashCroquis.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ApiFlashCroquis.wsgi.application'

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.environ.get('DB_NAME', BASE_DIR / 'db.sqlite3'),
        'USER': os.environ.get('DB_USER', ''),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', ''),
        'PORT': os.environ.get('DB_PORT', ''),
        'OPTIONS': {
            'charset': 'utf8mb4',
        } if os.environ.get('DB_ENGINE') == 'django.db.backends.mysql' else {},
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Ouagadougou'  # Burkina Faso timezone
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files (Uploaded files)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'EXCEPTION_HANDLER': 'flashcroquis.utils.custom_exception_handler',
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
    'DATE_FORMAT': '%Y-%m-%d',
    'TIME_FORMAT': '%H:%M:%S',
}

# Swagger/OpenAPI Configuration
SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    },
    'USE_SESSION_AUTH': False,
    'JSON_EDITOR': True,
    'SUPPORTED_SUBMIT_METHODS': [
        'get', 'post', 'put', 'delete', 'patch'
    ],
    'OPERATIONS_SORTER': 'alpha',
    'TAGS_SORTER': 'alpha',
    'DOC_EXPANSION': 'none',
    'DEEP_LINKING': True,
    'SHOW_EXTENSIONS': True,
    'DEFAULT_MODEL_RENDERING': 'model',
}

REDOC_SETTINGS = {
    'LAZY_RENDERING': False,
    'HIDE_HOSTNAME': False,
    'EXPAND_RESPONSES': [200, 201],
}

# CORS Configuration (Cross-Origin Resource Sharing)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React dev server
    "http://127.0.0.1:3000",
    "http://localhost:8080",  # Vue dev server
    "http://127.0.0.1:8080",
]

CORS_ALLOW_ALL_ORIGINS = DEBUG  # Only in development

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
            'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'flashcroquis': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'qgis': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Créer le répertoire des logs s'il n'existe pas
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# File Upload Settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_PERMISSIONS = 0o644

# Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Production Security Settings (activate only in production)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'KEY_PREFIX': 'flashcroquis',
        'TIMEOUT': 300,  # 5 minutes
    } if os.environ.get('REDIS_URL') else {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'flashcroquis-cache',
    }
}

# Session Configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_SAVE_EVERY_REQUEST = True

# Email Configuration
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@flashcroquis.com')

# FlashCroquis Specific Settings
FLASHCROQUIS_SETTINGS = {
    # QGIS Configuration
    'QGIS_INITIALIZATION_TIMEOUT': 30,  # seconds
    'QGIS_MAX_PROCESSING_TIME': 300,  # 5 minutes
    'QGIS_TEMP_DIR': BASE_DIR / 'temp' / 'qgis',
    'QGIS_FONT_DIR': BASE_DIR / 'fonts',
    
    # File Processing
    'MAX_LAYER_FILE_SIZE': 50 * 1024 * 1024,  # 50MB
    'ALLOWED_VECTOR_FORMATS': ['.shp', '.geojson', '.kml', '.gpx', '.csv'],
    'ALLOWED_RASTER_FORMATS': ['.tif', '.tiff', '.geotiff', '.jpg', '.png'],
    'TEMP_FILE_RETENTION_DAYS': 7,
    
    # Map Rendering
    'DEFAULT_MAP_WIDTH': 800,
    'DEFAULT_MAP_HEIGHT': 600,
    'MAX_MAP_WIDTH': 5000,
    'MAX_MAP_HEIGHT': 5000,
    'DEFAULT_DPI': 96,
    'MAX_DPI': 300,
    
    # PDF Generation
    'DEFAULT_PDF_QUALITY': 90,
    'MAX_PDF_SIZE': 100 * 1024 * 1024,  # 100MB
    'PDF_TEMPLATE_DIR': BASE_DIR / 'templates' / 'pdf',
    
    # Session Management
    'PROJECT_SESSION_TIMEOUT': 86400,  # 24 hours
    'MAX_SESSIONS_PER_USER': 10,
    'CLEANUP_INTERVAL': 3600,  # 1 hour
    
    # API Limits
    'API_RATE_LIMIT': '1000/hour',
    'BULK_OPERATION_LIMIT': 100,
    'CONCURRENT_PROCESSING_LIMIT': 5,
    
    # Geographic Settings
    'DEFAULT_CRS': 'EPSG:4326',
    'SUPPORTED_CRS': [
        'EPSG:4326',  # WGS84
        'EPSG:3857',  # Web Mercator
        'EPSG:32630', # UTM Zone 30N (Burkina Faso)
        'EPSG:2043',  # Burkina Faso TM
    ],
    
    # QR Code Settings
    'QR_CODE_MAX_LENGTH': 1000,
    'QR_CODE_PROCESSING_TIMEOUT': 10,
    
    # Parcelle Settings
    'MIN_PARCELLE_AREA': 1.0,  # 1 m²
    'MAX_PARCELLE_AREA': 1000000.0,  # 1 km²
    'MIN_PARCELLE_POINTS': 3,
    'MAX_PARCELLE_POINTS': 1000,
}

# Créer les répertoires nécessaires
for directory in [
    FLASHCROQUIS_SETTINGS['QGIS_TEMP_DIR'],
    FLASHCROQUIS_SETTINGS['PDF_TEMPLATE_DIR'],
    MEDIA_ROOT / 'projects',
    MEDIA_ROOT / 'layers',
    MEDIA_ROOT / 'generated',
    MEDIA_ROOT / 'renders',
]:
    os.makedirs(directory, exist_ok=True)

# Celery Configuration (pour les tâches asynchrones)
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300  # 5 minutes
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# Django Extensions (if installed)
if DEBUG:
    try:
        import django_extensions
        INSTALLED_APPS.append('django_extensions')
    except ImportError:
        pass

# Development Tools
if DEBUG:
    try:
        import debug_toolbar
        INSTALLED_APPS.append('debug_toolbar')
        MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
        INTERNAL_IPS = ['127.0.0.1', 'localhost']
        DEBUG_TOOLBAR_CONFIG = {
            'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
        }
    except ImportError:
        pass

# Health Check Configuration
HEALTH_CHECK_ENABLED = True
HEALTH_CHECK_ENDPOINTS = {
    'database': True,
    'cache': True,
    'qgis': True,
    'disk_space': True,
    'memory': True,
}

# Monitoring and Metrics
if os.environ.get('SENTRY_DSN'):
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        
        sentry_logging = LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR
        )
        
        sentry_sdk.init(
            dsn=os.environ.get('SENTRY_DSN'),
            integrations=[DjangoIntegration(), sentry_logging],
            traces_sample_rate=0.1,
            send_default_pii=True,
            environment=os.environ.get('ENVIRONMENT', 'development'),
        )
    except ImportError:
        pass