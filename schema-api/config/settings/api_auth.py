from config.env import env

TOKEN_KEY_LENGTH = env.int('SCHEMA_API_TOKEN_KEY_LENGTH', 8)
TOKEN_BYTE_LENGTH = env.int('SCHEMA_API_TOKEN_BYTE_LENGTH', 128)
AUTHORIZATION_HEADER_PREFIX = env.str('SCHEMA_API_AUTHORIZATION_HEADER_PREFIX', 'Bearer')
USE_AUTH = env.bool('SCHEMA_API_USE_AUTH', True)
MINIMUM_USERNAME_LENGTH = env.int('SCHEMA_API_MINIMUM_USERNAME_LENGTH', 1)

USERNAME_SLUG_PATTERN = env.str('SCHEMA_API_USERNAME_SLUG_PATTERN', None)
USERNAME_SLUG_PATTERN_VIOLATION_MESSAGE = env.str('SCHEMA_API_USERNAME_SLUG_PATTERN_VIOLATION_MESSAGE', None)
