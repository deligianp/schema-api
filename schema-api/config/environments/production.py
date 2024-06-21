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

LOGGING_CONF = {
    "FILES": {
        "DIRECTORY": env.str('SCHEMA_API_LOGS_DIRECTORY', None),
        'FILENAME': env.str('SCHEMA_API_LOGS_ACTIVITY_FILE_NAME', 'schema-api'),
        'ERROR_FILENAME': env.str('SCHEMA_API_LOGS_ERROR_FILE_NAME', None),
        'BYTES': env.int('SCHEMA_API_LOGS_FILE_SIZE_BYTES', 10 * 1024 * 1024),
        'BACKUP_COUNT': env.int('SCHEMA_API_LOGS_BACKUP_COUNT', 10)
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'base': {
            'format': '[{levelname}][{asctime}]: {message}',
            'style': '{'
        }
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'base'
        }
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

if LOGGING_CONF["FILES"]["DIRECTORY"]:
    LOGGING['handlers']['file'] = {
        'level': 'INFO',
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': f'{os.path.join(LOGGING_CONF["FILES"]["DIRECTORY"], LOGGING_CONF["FILES"]["FILENAME"])}.log',
        'maxBytes': LOGGING_CONF["FILES"]["BYTES"],
        'backupCount': LOGGING_CONF["FILES"]["BACKUP_COUNT"]
    }
    LOGGING['handlers']['error-file'] = {
        'level': 'ERROR',
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': f'{os.path.join(LOGGING_CONF["FILES"]["DIRECTORY"], LOGGING_CONF["FILES"]["ERROR_FILENAME"] or LOGGING_CONF["FILES"]["FILENAME"] + "-error")}.log',
        'maxBytes': LOGGING_CONF["FILES"]["BYTES"],
        'backupCount': LOGGING_CONF["FILES"]["BACKUP_COUNT"]
    }
    LOGGING['loggers']['']['handlers'].extend(['file', 'error-file'])
    LOGGING['loggers']['django']['handlers'].extend(['file', 'error-file'])

REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = [
    'rest_framework.throttling.AnonRateThrottle',
    'rest_framework.throttling.UserRateThrottle',
]
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '10/minute',
    'user': '20/minute',
}
