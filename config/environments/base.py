import os
from pathlib import Path
from config.settings.api import *
from config.settings.api_auth import *

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'django_filters',
    'api_auth',
    'api',
    'graphene_django',
    'drf_spectacular'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'schema_api.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'schema_api.wsgi.application'

# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = env.str('SCHEMA_API_LANGUAGE_CODE', 'en-us')

TIME_ZONE = env.str('SCHEMA_API_TIME_ZONE', 'UTC')

USE_I18N = env.bool('SCHEMA_API_USE_I18N', True)

USE_TZ = env.bool('SCHEMA_API_USE_TZ', True)

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static/')
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer'
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema'
}

GRAPHENE = {
    'SCHEMA': 'monitor.schema.schema'
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Schema API',
    'DESCRIPTION': 'A REST API for the scheduling and execution of containerized tasks',
    'VERSION': 'development',
    'SERVE_INCLUDE_SCHEMA': False,
    'PREPROCESSING_HOOKS': ["documentation.swagger.hooks.preprocessing_filter_spec"],
    'PARSER_WHITELIST': ['rest_framework.parsers.JSONParser'],
    'SWAGGER_UI_SETTINGS': {
        'defaultModelsExpandDepth': 10,
        'defaultModelExpandDepth': 10
    }
}

AUTH_USER_MODEL = 'api_auth.AuthEntity'

POSTGRES_DATABASE_CONFIGURATION = {
    'ENGINE': 'django.db.backends.postgresql',
    'USER': env.str('SCHEMA_API_DB_USER', 'schema-api'),
    'NAME': env.str('SCHEMA_API_DB_NAME', 'schema-api-db'),
    'HOST': env.str('SCHEMA_API_DB_HOST', '127.0.0.1'),
    'PORT': env.str('SCHEMA_API_DB_PORT', '5432'),
}

SQLITE_DATABASE_CONFIGURATION = {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': os.path.join(
        env.str('SCHEMA_API_SQLITE_DIRECTORY', BASE_DIR),
        f'{env.str("SCHEMA_API_DB_NAME", "schema-api-db")}.sqlite3'
    ),
}
