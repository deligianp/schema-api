import json
from urllib.parse import urlparse

from config.env import env

USE_FILES = env.bool('SCHEMA_API_USE_FILES', False)
S3 = {
    'URL': env.url('SCHEMA_API_S3_URL', '').geturl() or None,
    'ACCESS_KEY_ID': env.str('SCHEMA_API_S3_ACCESS_KEY_ID', None),
    'SECRET_ACCESS_KEY': env.str('SCHEMA_API_S3_SECRET_ACCESS_KEY', None),
    'VALIDITY_PERIOD_SECONDS': env.int('SCHEMA_API_S3_VALIDITY_PERIOD_SECONDS', 24 * 60 * 60),
    'MAX_PART_SIZE_BYTES': env.int('SCHEMA_API_S3_MAX_PART_SIZE_BYTES', 100 * 1024 * 1024),
    'USE_SSL': env.bool('SCHEMA_API_S3_USE_SSL', False),
    'VERIFY_SSL': env.bool('SCHEMA_API_S3_VERIFY_SSL', False),
    'CLIENT_PARAMETERS': json.loads(env.json('SCHEMA_API_S3_CLIENT_PARAMETERS', '{}'))
}
