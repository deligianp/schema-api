from config.environments.base import *

DEBUG = True
ALLOWED_HOSTS = []
SECRET_KEY = env.str('SECRET_KEY', 'insecure-secret-key')

if env.bool('USE_POSTGRES', False):
    DATABASES = {
        'default': {
            'PASSWORD': env.str('SCHEMA_API_DB_PASSWORD'),
            **POSTGRES_DATABASE_CONFIGURATION
        }
    }
else:
    DATABASES = {
        'default': SQLITE_DATABASE_CONFIGURATION
    }
