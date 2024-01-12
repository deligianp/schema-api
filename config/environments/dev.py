from config.environments.base import *

DEBUG = True
ALLOWED_HOSTS = env.list('SCHEMA_API_ALLOWED_HOSTS', default=['*'])
SECRET_KEY = env.str('SECRET_KEY', None)
if not SECRET_KEY:
    SECRET_KEY_PATH = env.str('SCHEMA_API_SECRET_KEY_FILE', None)
    if not SECRET_KEY_PATH:
        SECRET_KEY = 'insecure-secret-key'
    else:
        with open(SECRET_KEY_PATH, 'r', encoding='utf-8') as secret_key_file:
            SECRET_KEY = secret_key_file.read().strip()

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
