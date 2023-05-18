from config.environments.base import *

DEBUG = False
ALLOWED_HOSTS = env.list('SCHEMA_API_ALLOWED_HOSTS')
SECRET_KEY = env.str('SCHEMA_API_SECRET_KEY')
DATABASES = {
    'default': {
        'PASSWORD': env.str('SCHEMA_API_DB_PASSWORD'),
        **POSTGRES_DATABASE_CONFIGURATION
    }
}
