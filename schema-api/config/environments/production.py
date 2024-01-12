from config.environments.base import *

DEBUG = False
ALLOWED_HOSTS = env.list('SCHEMA_API_ALLOWED_HOSTS')
SECRET_KEY = env.str('SCHEMA_API_SECRET_KEY', None)
if not SECRET_KEY:
    SECRET_KEY_PATH = env.str('SCHEMA_API_SECRET_KEY_FILE')
    with open(SECRET_KEY_PATH, 'r', encoding='utf-8') as secret_key_file:
        SECRET_KEY = secret_key_file.read().strip()
DATABASES = {
    'default': {
        'PASSWORD': env.str('SCHEMA_API_DB_PASSWORD'),
        **POSTGRES_DATABASE_CONFIGURATION
    }
}
